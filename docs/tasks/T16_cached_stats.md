# T16: Фоновый расчёт cached_stats

## Цель
Celery-задача, рассчитывающая базовые метрики виртуального датасета после создания.

## Контекст
- `01_DATA_MODEL.md` раздел "Кэшированная статистика виртуального датасета"
- `02_DOMAIN_LOGIC.md` все модули duration, rework, variants

## DoD
- [ ] Celery-task `compute_virtual_dataset_stats(vd_id)` в `app/tasks/compute_stats.py`.
- [ ] Загружает event log → применяет role_mapping → применяет фильтры из config → считает все метрики.
- [ ] Записывает результат в `virtual_datasets.cached_stats` (JSONB).
- [ ] Поле `computed_at` в stats отмечает время расчёта.
- [ ] `GET /virtual-datasets/{id}` возвращает stats=null если ещё не посчитано.
- [ ] UI: пока stats=null — показывать spinner с сообщением "Считается статистика...".

## Реализация

```python
@celery_app.task
def compute_virtual_dataset_stats(vd_id: int):
    async def run():
        async with AsyncSessionLocal() as db:
            vd = await db.get(VirtualDataset, vd_id)
            if not vd:
                return
            
            repo = PostgresEventLogRepository(db)
            df = await repo.load_to_dataframe(vd.physical_dataset_id)
            
            # Применяем фильтры из config
            filters = vd.config.get("filters", {})
            if filters:
                from app.domain.mining.filters import apply_filter, EventFilter
                df = apply_filter(df, EventFilter(**filters))
            
            # Применяем role mapping
            from app.domain.mining.role_mapping import apply_role_mapping
            df = apply_role_mapping(df, vd.role_mapping_snapshot["mapping"])
            
            # Считаем все метрики
            from app.domain.mining import duration, rework, variants
            
            case_dur = duration.compute_case_duration(df)
            comparison = rework.compute_duration_comparison(df)
            
            stats = {
                "total_cases": int(df["case_id"].nunique()),
                "total_events": int(len(df)),
                "unique_activities": int(df["activity"].nunique()),
                "unique_resources": int(df["resource"].nunique()) if "resource" in df.columns else 0,
                "unique_departments": int(df["department"].nunique()) if "department" in df.columns else 0,
                "period_start": df["timestamp_start"].min().isoformat() if len(df) else None,
                "period_end": df["timestamp_end"].max().isoformat() if len(df) else None,
                "avg_case_duration_seconds": float(case_dur["duration_seconds"].mean()),
                "avg_case_duration_with_rework_seconds": comparison["avg_duration_with_rework_seconds"],
                "avg_case_duration_without_rework_seconds": comparison["avg_duration_without_rework_seconds"],
                "cases_with_rework": comparison["n_cases_with_rework"],
                "cases_without_rework": comparison["n_cases_without_rework"],
                "global_rework_pct": rework.compute_global_rework_pct(df),
                "unique_traces": int(variants.get_case_traces(df).nunique()),
                "variability_pct": variants.compute_variability_pct(df),
                "mean_occurrence_pct": variants.compute_mean_occurrence_pct(df),
                "computed_at": datetime.now(timezone.utc).isoformat(),
            }
            
            vd.cached_stats = stats
            await db.commit()
    
    asyncio.run(run())
```

## Тесты
- `test_stats_match_golden_metrics` — после расчёта stats совпадает с golden_data/expected_metrics.json.

## Acceptance
Через 3-10 секунд после создания VD на основе synthetic_log.xlsx — в БД появляется cached_stats со значениями, совпадающими с golden.
