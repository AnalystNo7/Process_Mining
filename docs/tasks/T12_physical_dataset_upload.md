# T12: Загрузка физического датасета (preview + upload)

## Цель
2-шаговая загрузка xlsx с маппингом колонок: preview → upload (через Celery).

## Контекст
- `03_API.md` раздел "4. Физические датасеты"
- `04_UI.md` раздел "5. Мастер загрузки физ. датасета"
- `T11_xlsx_loading.md`

## DoD
- [ ] `POST /projects/{id}/physical-datasets/preview` принимает файл, парсит, возвращает превью + suggested mapping + preview_token.
- [ ] `POST /projects/{id}/physical-datasets` принимает preview_token + final mapping, запускает Celery-задачу `upload_dataset_task`.
- [ ] Celery-задача: парсит файл через `load_event_log`, валидирует, дедуплицирует, вставляет через `event_log_repo.bulk_insert`, обновляет статус physical_dataset.
- [ ] Прогресс задачи доступен через `GET /tasks/{task_id}`.
- [ ] UI: AntD Steps с 3 шагами (Файл → Маппинг → Прогресс).
- [ ] Сохранение шаблона: чекбокс "Save as template" → создаёт/обновляет upload_template.
- [ ] Применение шаблона: dropdown в шаге 2.
- [ ] Auto-suggested mapping: для каждого стандартного поля пытаемся найти колонку по похожему имени (case-insensitive contains).

## Реализация

### `app/services/physical_dataset_service.py`
```python
async def preview_upload(file: UploadFile, project_id: int) -> PreviewResponse:
    # Сохранить файл во временное хранилище
    token = uuid4().hex
    tmp_path = settings.STORAGE_PATH / "tmp" / f"{token}.xlsx"
    tmp_path.parent.mkdir(exist_ok=True, parents=True)
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    # Прочитать первые 10 строк
    df = pd.read_excel(tmp_path, nrows=10)
    full_count = pd.read_excel(tmp_path, sheet_name=0).shape[0]  # для счёта
    
    # Авто-suggest mapping
    suggested = suggest_column_mapping(df.columns.tolist())
    
    columns = [
        {"name": col, "sample_values": df[col].dropna().head(3).astype(str).tolist(),
         "dtype": infer_dtype(df[col])}
        for col in df.columns
    ]
    
    return PreviewResponse(
        columns=columns,
        preview_rows=df.head(10).fillna("").to_dict(orient="records"),
        total_rows=full_count,
        suggested_mapping=suggested,
        preview_token=token,
    )


def suggest_column_mapping(columns: list[str]) -> dict:
    """Эвристика: ищем по похожим именам."""
    PATTERNS = {
        "case_id": ["doc_id", "case_id", "case", "id_документа"],
        "activity": ["операция", "activity", "task", "action"],
        "timestamp_start": ["in_progress", "start", "начало", "from"],
        "timestamp_end": ["completed", "end", "конец", "to"],
        "resource": ["task_user", "user", "исполнитель", "resource"],
        "department": ["department", "подразделение", "task_user_department"],
    }
    result = {}
    for std, patterns in PATTERNS.items():
        for col in columns:
            if any(p.lower() in col.lower() for p in patterns):
                result[std] = col
                break
    return result
```

### Celery-задача
```python
@celery_app.task(bind=True)
def upload_dataset_task(self, dataset_id: int, preview_token: str, project_id: int):
    """Долгая обработка: парсинг, валидация, вставка."""
    self.update_state(state="STARTED", meta={"progress": 5})
    
    # Найти tmp файл
    tmp_path = settings.STORAGE_PATH / "tmp" / f"{preview_token}.xlsx"
    
    # Перенести в постоянное хранилище
    final_path = settings.STORAGE_PATH / "projects" / str(project_id) / f"physical_{dataset_id}.xlsx"
    final_path.parent.mkdir(exist_ok=True, parents=True)
    shutil.move(tmp_path, final_path)
    
    self.update_state(state="STARTED", meta={"progress": 20})
    
    # Загрузить
    async def run():
        async with AsyncSessionLocal() as db:
            ds = await db.get(PhysicalDataset, dataset_id)
            ds.status = "validating"
            await db.commit()
            
            df = load_event_log(final_path, ds.column_mapping)
            report = validate_event_log(df)
            if report.errors:
                ds.status = "failed"
                ds.error_message = "; ".join(report.errors)
                await db.commit()
                return
            
            df, n_dups = deduplicate(df)
            
            self.update_state(state="STARTED", meta={"progress": 50})
            
            repo = PostgresEventLogRepository(db)
            await repo.bulk_insert(dataset_id, df)
            
            self.update_state(state="STARTED", meta={"progress": 90})
            
            # Заполняем статистику
            ds.total_events = len(df)
            ds.total_cases = df["case_id"].nunique()
            ds.unique_activities = df["activity"].nunique()
            ds.period_start = df["timestamp_start"].min()
            ds.period_end = df["timestamp_end"].max()
            
            # Health check (T13)
            health = health_check(df)
            ds.health_status = health.status
            ds.health_report = {"checks": [asdict(c) for c in health.checks]}
            
            ds.status = "ready"
            await db.commit()
    
    asyncio.run(run())
    return {"dataset_id": dataset_id}
```

### UI
React-компоненты для 3 шагов AntD Steps + axios upload + polling `/tasks/{task_id}` каждые 2 сек.

## Тесты
- `test_preview_returns_columns_and_suggested_mapping`.
- `test_upload_dataset_full_flow` (integration с реальным xlsx из golden).
- `test_upload_fails_when_required_column_missing`.
- `test_template_saved_when_flag_set`.

## Acceptance
В UI можно пройти 3 шага мастера, загрузить `synthetic_log.xlsx`, увидеть прогресс, после завершения — физ.датасет в списке со статусом ready и метаданными.
