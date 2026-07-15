import hashlib
from dataclasses import asdict
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from fastapi import Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, EntityNotFoundError
from app.db.models.datasets import PhysicalDataset, VirtualDataset
from app.db.models.projects import UploadTemplate
from app.db.models.users import User
from app.db.repositories.event_log import PostgresEventLogRepository
from app.domain.mining.health import health_check
from app.domain.mining.loading import load_event_log, validate_event_log
from app.schemas.physical_datasets import (
    ColumnInfo,
    PhysicalDatasetCreate,
    PreviewResponse,
    SheetInfo,
)
from app.services import audit_service, role_mapping_service

# Эвристика авто-сопоставления колонок файла стандартным полям.
_SUGGEST_PATTERNS: dict[str, list[str]] = {
    "case_id": ["doc_id", "case_id", "case", "идентификатор"],
    "activity": ["операция", "activity", "task", "action", "шаг"],
    "timestamp_start": ["in_progress", "start", "начало", "from"],
    "timestamp_end": ["completed", "end", "конец", "окончание", "to"],
    "resource": ["task_user", "user", "исполнитель", "resource"],
    "department": ["department", "подразделение", "task_user_department"],
}


def _tmp_dir() -> Path:
    path = settings.STORAGE_PATH / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def suggest_column_mapping(columns: list[str]) -> dict[str, str]:
    """Подбирает соответствие стандартных полей колонкам файла по именам."""
    result: dict[str, str] = {}
    for std_field, patterns in _SUGGEST_PATTERNS.items():
        for col in columns:
            if any(p.lower() in col.lower() for p in patterns):
                result[std_field] = col
                break
    return result


def _infer_dtype(series: pd.Series) -> str:
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_numeric_dtype(series):
        return "number"
    return "string"


# Сколько первых строк файла показываем в пикере строки заголовков.
_RAW_PREVIEW_ROWS = 15


def _suggest_header_row(raw_head: pd.DataFrame) -> int:
    """Подсказка строки заголовков: первая строка с максимумом непустых ячеек
    (шапка отчёта обычно заполнена частично, строка заголовков — целиком)."""
    counts = raw_head.notna().sum(axis=1)
    if counts.empty:
        return 0
    return int(counts.idxmax())


def _sheet_infos(tmp_path: Path) -> list[SheetInfo]:
    """Список листов файла с числом строк данных на каждом.

    ExcelFile закрываем явно: иначе на Windows незакрытый дескриптор блокирует
    последующее удаление temp-файла (WinError 32) при создании датасета."""
    with pd.ExcelFile(tmp_path) as xl:
        return [
            SheetInfo(name=str(name), rows=int(len(xl.parse(name, header=None))))
            for name in xl.sheet_names
        ]


def _suggest_sheet(infos: list[SheetInfo]) -> str:
    """Подсказка листа: с наибольшим числом строк (для сводных файлов это
    обычно основной лист). При равенстве/пустых — первый по порядку."""
    if not infos:
        raise ValueError("В файле нет листов")
    return max(infos, key=lambda s: s.rows).name if any(
        s.rows for s in infos
    ) else infos[0].name


def _build_preview(
    tmp_path: Path, token: str, sheet_name: str | None, header_row: int | None
) -> PreviewResponse:
    """Собирает превью: список листов + сырые строки для пикера заголовка +
    разбор выбранного листа с заданной (или подсказанной) строкой заголовков."""
    sheets = _sheet_infos(tmp_path)
    if sheet_name is None:
        sheet_name = _suggest_sheet(sheets)
    elif sheet_name not in {s.name for s in sheets}:
        raise ValueError(f"Лист {sheet_name!r} не найден в файле")

    raw_head = pd.read_excel(
        tmp_path, sheet_name=sheet_name, header=None, nrows=_RAW_PREVIEW_ROWS
    )
    raw_rows: list[list[str]] = raw_head.fillna("").astype(str).values.tolist()
    if header_row is None:
        header_row = _suggest_header_row(raw_head)
    elif header_row >= len(raw_head):
        raise ValueError(
            f"Строка заголовков {header_row + 1} выходит за пределы листа"
        )

    raw = pd.read_excel(tmp_path, sheet_name=sheet_name, header=header_row)
    columns = [
        ColumnInfo(
            name=str(col),
            sample_values=[str(v) for v in raw[col].dropna().head(3).tolist()],
            dtype=_infer_dtype(raw[col]),
        )
        for col in raw.columns
    ]
    preview_rows: list[dict[str, Any]] = (
        raw.head(10).fillna("").astype(str).to_dict(orient="records")
    )
    return PreviewResponse(
        columns=columns,
        preview_rows=preview_rows,
        total_rows=int(len(raw)),
        suggested_mapping=suggest_column_mapping([str(c) for c in raw.columns]),
        preview_token=token,
        raw_rows=raw_rows,
        header_row=header_row,
        sheets=sheets,
        sheet_name=sheet_name,
    )


async def preview_upload(file: UploadFile) -> PreviewResponse:
    """Сохраняет файл во временное хранилище, возвращает превью и маппинг.
    Лист и строка заголовков подбираются автоматически (уточняются reparse)."""
    token = uuid4().hex
    tmp_path = _tmp_dir() / f"{token}.xlsx"
    tmp_path.write_bytes(await file.read())
    return _build_preview(tmp_path, token, sheet_name=None, header_row=None)


async def reparse_preview(
    preview_token: str, sheet_name: str, header_row: int | None
) -> PreviewResponse:
    """Повторный разбор ранее загруженного файла с другим листом и/или строкой
    заголовков (без повторной загрузки). header_row=None — переподсказать для
    выбранного листа (используется при смене листа)."""
    tmp_path = _tmp_dir() / f"{preview_token}.xlsx"
    if not tmp_path.exists():
        raise EntityNotFoundError("preview_token недействителен или истёк")
    return _build_preview(tmp_path, preview_token, sheet_name, header_row)


async def create_physical_dataset(
    db: AsyncSession,
    project_id: int,
    payload: PhysicalDatasetCreate,
    actor: User,
    request: Request | None = None,
) -> PhysicalDataset:
    """Создаёт запись физ.датасета (статус validating). Обработка — в Celery."""
    tmp_path = _tmp_dir() / f"{payload.preview_token}.xlsx"
    if not tmp_path.exists():
        raise EntityNotFoundError("preview_token недействителен или истёк")

    content = tmp_path.read_bytes()
    project_dir = settings.STORAGE_PATH / "projects" / str(project_id)
    project_dir.mkdir(parents=True, exist_ok=True)

    dataset = PhysicalDataset(
        project_id=project_id,
        name=payload.name,
        file_name=f"{payload.name}.xlsx",
        file_size_bytes=len(content),
        file_hash=hashlib.sha256(content).hexdigest(),
        storage_path="",
        column_mapping=payload.column_mapping,
        header_row=payload.header_row,
        sheet_name=payload.sheet_name,
        total_events=0,
        total_cases=0,
        unique_activities=0,
        health_status="good",
        health_report={},
        uploaded_by=actor.id,
        status="validating",
    )
    db.add(dataset)
    await db.flush()

    final_path = project_dir / f"physical_{dataset.id}.xlsx"
    final_path.write_bytes(content)
    dataset.storage_path = str(final_path)
    # Уборка temp-файла — best-effort: если он кратко занят (Windows —
    # антивирус/индексатор), это не повод срывать уже успешную загрузку.
    try:
        tmp_path.unlink(missing_ok=True)
    except OSError:
        pass

    if payload.save_as_template:
        db.add(
            UploadTemplate(
                project_id=project_id,
                name=f"Шаблон: {payload.name}",
                column_mapping=payload.column_mapping,
                header_row=payload.header_row,
                sheet_name=payload.sheet_name,
                is_default=False,
            )
        )

    await audit_service.log_event(
        db, actor, "physical_dataset.upload", "physical_dataset", dataset.id,
        request=request, metadata={"name": dataset.name},
    )
    await db.commit()
    await db.refresh(dataset)
    return dataset


async def process_upload(
    db: AsyncSession, dataset: PhysicalDataset, file_path: Path
) -> None:
    """Обрабатывает загруженный файл: парсинг → валидация → запись в event_log
    → статистика и health-check. Вызывается из Celery-задачи (T12) и тестов.

    Дедупликация НЕ применяется — продакшн-метрики должны совпадать с эталоном
    (expected_metrics.json вычислен на недедуплицированном логе)."""
    dataset.status = "validating"
    await db.commit()

    try:
        sheet = dataset.sheet_name if dataset.sheet_name is not None else 0
        df = load_event_log(
            file_path, dataset.column_mapping, dataset.header_row, sheet
        )
    except Exception as exc:  # noqa: BLE001 — любая ошибка парсинга → failed
        dataset.status = "failed"
        dataset.error_message = f"Ошибка чтения файла: {exc}"
        await db.commit()
        return

    report = validate_event_log(df)
    if report.errors:
        dataset.status = "failed"
        dataset.error_message = "; ".join(report.errors)
        await db.commit()
        return

    repo = PostgresEventLogRepository(db)
    await repo.bulk_insert(dataset.id, df)

    dataset.total_events = int(len(df))
    dataset.total_cases = int(df["case_id"].nunique())
    dataset.unique_activities = int(df["activity"].nunique())
    dataset.period_start = df["timestamp_start"].min().to_pydatetime()
    dataset.period_end = df["timestamp_end"].max().to_pydatetime()

    report_health = health_check(df)
    dataset.health_status = report_health.status
    dataset.health_report = {"checks": [asdict(c) for c in report_health.checks]}

    # Новые подразделения из датасета → в маппинг ролей как «Не размечено».
    departments = [
        str(d) for d in df["department"].dropna().unique().tolist() if d
    ]
    await role_mapping_service.ensure_departments_mapped(
        db, dataset.project_id, departments
    )

    dataset.status = "ready"
    await db.commit()


async def list_physical_datasets(
    db: AsyncSession, project_id: int
) -> tuple[list[PhysicalDataset], int]:
    stmt = (
        select(PhysicalDataset)
        .where(PhysicalDataset.project_id == project_id)
        .order_by(PhysicalDataset.uploaded_at.desc())
    )
    items = list((await db.scalars(stmt)).all())
    return items, len(items)


async def get_physical_dataset(
    db: AsyncSession, project_id: int, dataset_id: int
) -> PhysicalDataset:
    dataset = await db.get(PhysicalDataset, dataset_id)
    if dataset is None or dataset.project_id != project_id:
        raise EntityNotFoundError(f"Физический датасет с id={dataset_id} не найден")
    return dataset


async def delete_physical_dataset(
    db: AsyncSession,
    project_id: int,
    dataset_id: int,
    actor: User,
    request: Request | None = None,
) -> None:
    dataset = await get_physical_dataset(db, project_id, dataset_id)
    linked = await db.scalar(
        select(func.count())
        .select_from(VirtualDataset)
        .where(VirtualDataset.physical_dataset_id == dataset_id)
    )
    if linked:
        raise ConflictError(
            "Сначала удалите связанные виртуальные датасеты "
            f"({linked} шт.)"
        )
    storage_path = dataset.storage_path
    await db.delete(dataset)
    await audit_service.log_event(
        db, actor, "physical_dataset.delete", "physical_dataset", dataset_id,
        request=request,
    )
    await db.commit()
    if storage_path:
        Path(storage_path).unlink(missing_ok=True)
