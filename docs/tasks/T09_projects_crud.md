# T09: CRUD проектов

## Цель
API + UI для создания и управления проектами.

## Контекст
- `03_API.md` раздел "3. Проекты"
- `04_UI.md` раздел "2. Список проектов", "3. Создание проекта", "4. Обзор проекта"
- `01_DATA_MODEL.md` таблица `core.projects`

## DoD
- [ ] Эндпоинты: `GET /projects`, `POST /projects`, `GET /projects/{id}`, `PATCH /projects/{id}`, `DELETE /projects/{id}`.
- [ ] Сервис `project_service.py` с `create`, `get`, `list`, `update`, `delete`.
- [ ] При создании проекта автоматически создаётся пустой role_mapping (версия 1) и upload_template со стандартным маппингом TESSA.
- [ ] Все аналитики видят все проекты (нет фильтрации по правам на чтение).
- [ ] Изменять и удалять может только создатель и админ — иначе 403.
- [ ] Soft delete (`is_deleted=true`), удалённые не показываются в списке.
- [ ] Audit log на create/update/delete.
- [ ] UI: страница `/projects` со списком карточек, страница `/projects/new` с формой, страница `/projects/:id` с табами (Обзор/Датасеты/Виртуальные/Маппинг/SLA/Настройки) — пока с заглушками для табов, которые ещё не реализованы.

## Реализация

### Pydantic
```python
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    created_by: UserBriefResponse
    created_at: datetime
    physical_datasets_count: int
    virtual_datasets_count: int
    dashboards_count: int
```

### Стандартный шаблон TESSA при создании проекта
```python
DEFAULT_TESSA_TEMPLATE = {
    "case_id": "doc_id",
    "activity": "Операция",
    "timestamp_start": "in_progress_datetime",
    "timestamp_end": "completed_datetime",
    "resource": "task_user",
    "department": "task_user_department",
    "additional": {
        "doc_type": "doc_type",
        "doc_number": "doc_number",
        "kr_state": "kr_state",
        "head_user_name": "head_user_name",
        "route_type": "route_type",
        "group_name": "group_name",
    },
}
```

### Зависимость `require_project_owner_or_admin`
```python
async def require_project_owner_or_admin(
    project_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = await db.get(Project, project_id)
    if not project or project.is_deleted:
        raise HTTPException(404)
    if user.role != "admin" and project.created_by != user.id:
        raise HTTPException(403, "Only project owner or admin can modify")
    return project
```

### UI
- `ProjectsPage`: AntD `Card` grid + кнопка `+ Создать проект` → модалка или редирект на `/projects/new`.
- `ProjectDetailsPage`: AntD `Tabs` с вкладками. На каждой вкладке — пока что текст-заглушка "Будет реализовано в задаче T??".

## Тесты
- `test_create_project_creates_default_template_and_mapping`.
- `test_list_projects_returns_all`.
- `test_update_project_only_owner_or_admin`.
- `test_delete_project_soft_delete`.
- `test_deleted_project_not_in_list`.

## Acceptance
В UI можно создать проект, увидеть его в списке, открыть детали, переименовать, удалить.
