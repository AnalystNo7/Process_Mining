# T15: Создание виртуального датасета со snapshot

## Цель
Виртуальный датасет = immutable снимок маппинга ролей + SLA + конфигурации фильтров поверх физического.

## Контекст
- `01_DATA_MODEL.md` раздел "Виртуальный датасет"
- `03_API.md` раздел "8. Виртуальные датасеты"

## DoD
- [ ] `POST /virtual-datasets` принимает physical_dataset_id, name, config с фильтрами.
- [ ] При создании автоматически snapshot текущей версии role_mapping и SLA-правил в JSONB-полях.
- [ ] Запуск фоновой задачи `compute_virtual_dataset_stats` (см. T16).
- [ ] `GET /virtual-datasets/{id}` возвращает все данные включая snapshot и cached_stats.
- [ ] `DELETE /virtual-datasets/{id}` (только владелец/админ).
- [ ] Если у проекта нет ни одного role_mapping (что не должно быть, но защита) — выдаётся warning через 422 с указанием.
- [ ] Если SLA пуст — это нормально, snapshot = пустой массив, SLA-метрики просто будут недоступны.
- [ ] UI: после загрузки физ.датасета — кнопка "Создать виртуальный датасет", открывает мастер: выбор маппинга ролей (или редактирование), опциональные фильтры (период, doc_type), кнопка "Создать". После создания — редирект на экран ожидания статистики, потом — на стандартный дашборд.

## Реализация

```python
async def create_virtual_dataset(
    db: AsyncSession,
    project_id: int,
    physical_dataset_id: int,
    request: VirtualDatasetCreate,
    user: User,
) -> VirtualDataset:
    # Берём текущий role_mapping
    role_mapping = await db.scalar(
        select(RoleMapping)
        .where(RoleMapping.project_id == project_id)
        .order_by(RoleMapping.version.desc())
    )
    if not role_mapping:
        raise ValidationError("Project has no role mapping")
    
    # Берём текущие SLA-правила (на дату сегодня)
    today = date.today()
    sla_rules = await db.execute(
        select(SLARule)
        .where(SLARule.project_id == project_id,
               SLARule.effective_from <= today,
               or_(SLARule.effective_until.is_(None), SLARule.effective_until > today))
    )
    sla_list = sla_rules.scalars().all()
    
    # Создаём виртуальный датасет
    vd = VirtualDataset(
        project_id=project_id,
        physical_dataset_id=physical_dataset_id,
        name=request.name,
        description=request.description,
        role_mapping_snapshot={
            "version": role_mapping.version,
            "mapping": role_mapping.mapping,
            "roles": role_mapping.roles,
        },
        sla_rules_snapshot=[
            {"id": r.id, "role": r.role, "operation_pattern": r.operation_pattern,
             "sla_value": float(r.sla_value), "sla_unit": r.sla_unit,
             "tolerance_hours": float(r.tolerance_hours),
             "target_compliance_pct": float(r.target_compliance_pct)}
            for r in sla_list
        ],
        config=request.config or {},
        cached_stats=None,
        created_by=user.id,
        is_personal=True,
    )
    db.add(vd)
    await db.commit()
    await db.refresh(vd)
    
    # Запуск фоновой задачи
    compute_virtual_dataset_stats.delay(vd.id)
    
    return vd
```

## Тесты
- `test_create_vd_snapshots_current_role_mapping_version`.
- `test_update_role_mapping_does_not_affect_existing_vd`.
- `test_create_vd_with_empty_sla_works`.
- `test_delete_vd_only_owner`.

## Acceptance
Аналитик создаёт VD, в БД виден snapshot текущего mapping. После изменения mapping — старый VD по-прежнему ссылается на старую версию.
