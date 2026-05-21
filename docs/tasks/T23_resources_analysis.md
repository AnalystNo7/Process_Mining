# T23: Анализ исполнителей

## Цель
Таблица "Исполнитель | кейсов | событий | ср.длительность операций".

## Контекст
- `02_DOMAIN_LOGIC.md` раздел "domain/mining/resources.py"

## DoD
- [ ] Функция `compute_resource_workload(df)`.
- [ ] Эндпоинт `GET /analytics/resources` с сортировкой и лимитом.
- [ ] Поддержка drill-down: для конкретного исполнителя — список кейсов.
- [ ] Unit-тесты.

## Реализация
```python
def compute_resource_workload(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("resource").agg(
        n_cases=("case_id", "nunique"),
        n_events=("activity", "count"),
        avg_own_duration_seconds=("own_duration_sec", "mean"),
        n_unique_activities=("activity", "nunique"),
    ).reset_index().sort_values("n_events", ascending=False)
```

## Acceptance
Endpoint возвращает топ-50 исполнителей на synthetic_log с корректными цифрами.
