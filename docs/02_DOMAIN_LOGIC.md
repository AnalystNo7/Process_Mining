# 02. Доменная логика и алгоритмы process mining

## Назначение

В этом файле — все алгоритмы расчёта метрик process mining, которые система должна реализовывать. Для каждого алгоритма дан **псевдокод**, ожидаемое поведение и привязка к golden-test эталонам.

**Все алгоритмы должны иметь чистые функции** на pandas DataFrame — это упрощает тестирование. Бизнес-логика отделена от слоя доступа к данным.

## Модуль `domain/mining/loading.py` — загрузка и валидация

### Чтение xlsx и применение маппинга

```python
def load_event_log(
    file_path: Path,
    column_mapping: ColumnMapping,
) -> pd.DataFrame:
    """
    Загружает xlsx, применяет маппинг колонок, возвращает стандартизованный DataFrame.
    
    column_mapping: {
        "case_id": "doc_id",
        "activity": "Операция",
        "timestamp_start": "in_progress_datetime",
        "timestamp_end": "completed_datetime",
        "resource": "task_user",          # optional
        "department": "task_user_department",  # optional
        "additional": {"doc_type": "doc_type", ...}  # optional
    }
    
    Возвращает DataFrame с обязательными колонками:
      case_id, activity, timestamp_start, timestamp_end
    Опциональными:
      resource, department
    И колонкой 'attributes' (dict) со всеми additional-полями.
    """
    df = pd.read_excel(file_path, sheet_name=0)
    
    # Маппим обязательные колонки
    required = ['case_id', 'activity', 'timestamp_start', 'timestamp_end']
    for std_name in required:
        src_col = column_mapping[std_name]
        if src_col not in df.columns:
            raise ValidationError(f"Колонка {src_col!r} отсутствует в файле")
    
    result = pd.DataFrame()
    result['case_id'] = df[column_mapping['case_id']].astype(str)
    result['activity'] = df[column_mapping['activity']].astype(str)
    
    # Парсинг timestamp: Excel-числа → datetime
    result['timestamp_start'] = parse_excel_datetime(df[column_mapping['timestamp_start']])
    result['timestamp_end'] = parse_excel_datetime(df[column_mapping['timestamp_end']])
    
    # Опциональные
    for opt in ['resource', 'department']:
        src_col = column_mapping.get(opt)
        if src_col and src_col in df.columns:
            result[opt] = df[src_col].astype(str).replace('nan', None)
        else:
            result[opt] = None
    
    # Доп. атрибуты → JSON dict в каждой строке
    additional = column_mapping.get('additional', {})
    if additional:
        attrs_df = pd.DataFrame()
        for std_name, src_col in additional.items():
            if src_col in df.columns:
                attrs_df[std_name] = df[src_col]
        result['attributes'] = attrs_df.to_dict(orient='records')
    else:
        result['attributes'] = [{}] * len(result)
    
    # Локализуем datetime в МСК → UTC для хранения
    result['timestamp_start'] = result['timestamp_start'].dt.tz_localize('Europe/Moscow').dt.tz_convert('UTC')
    result['timestamp_end'] = result['timestamp_end'].dt.tz_localize('Europe/Moscow').dt.tz_convert('UTC')
    
    return result
```

### Валидация после загрузки

```python
def validate_event_log(df: pd.DataFrame) -> ValidationReport:
    """
    Проверки:
      1. Нет NULL в обязательных полях (case_id, activity, timestamp_start, timestamp_end)
      2. timestamp_end >= timestamp_start (для всех строк)
      3. Есть хотя бы 1 событие
      4. Есть хотя бы 1 кейс
      5. case_id не пустые строки
    
    Возвращает отчёт со списком проблем. Если есть errors — загрузка падает.
    """
    errors = []
    warnings = []
    
    if len(df) == 0:
        errors.append("Файл не содержит ни одной строки данных")
        return ValidationReport(errors=errors, warnings=warnings)
    
    for col in ['case_id', 'activity', 'timestamp_start', 'timestamp_end']:
        n_nulls = df[col].isna().sum()
        if n_nulls > 0:
            errors.append(f"Колонка {col!r} содержит {n_nulls} пустых значений")
    
    if (df['timestamp_end'] < df['timestamp_start']).any():
        n_bad = (df['timestamp_end'] < df['timestamp_start']).sum()
        errors.append(f"В {n_bad} строках timestamp_end раньше timestamp_start")
    
    n_zero_dur = (df['timestamp_end'] == df['timestamp_start']).sum()
    if n_zero_dur / len(df) > 0.8:
        warnings.append(
            f"{n_zero_dur} операций ({n_zero_dur/len(df)*100:.1f}%) имеют нулевую длительность. "
            "Это нормально для системных событий СЭД, но повлияет на метрики собственной длительности."
        )
    
    return ValidationReport(errors=errors, warnings=warnings)
```

### Удаление дубликатов

```python
def deduplicate(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """
    Удаляет точные дубликаты по (case_id, activity, timestamp_start, timestamp_end, resource).
    Возвращает (очищенный_df, кол-во_удалённых).
    """
    before = len(df)
    dedup_cols = ['case_id', 'activity', 'timestamp_start', 'timestamp_end']
    if 'resource' in df.columns:
        dedup_cols.append('resource')
    deduped = df.drop_duplicates(subset=dedup_cols, keep='first')
    return deduped, before - len(deduped)
```

## Модуль `domain/mining/health.py` — Health Check датасета

```python
@dataclass
class HealthReport:
    status: Literal['good', 'warning', 'poor']
    checks: list[HealthCheck]
    
@dataclass
class HealthCheck:
    name: str
    severity: Literal['info', 'warning', 'error']
    message: str
    value: Any

def health_check(df: pd.DataFrame) -> HealthReport:
    """
    Проверяет пригодность датасета для анализа.
    Возвращает отчёт с цветовой меткой:
      - good: все проверки прошли
      - warning: есть warning, но анализ возможен
      - poor: есть errors, анализ может дать неверные выводы
    """
    checks = []
    
    n_cases = df['case_id'].nunique()
    n_events = len(df)
    n_unique_activities = df['activity'].nunique()
    
    # 1. Минимум кейсов
    if n_cases < 50:
        checks.append(HealthCheck('cases_count', 'error',
            f"Только {n_cases} кейсов. Статистически недостаточно для надёжного анализа (минимум 50).",
            n_cases))
    elif n_cases < 200:
        checks.append(HealthCheck('cases_count', 'warning',
            f"{n_cases} кейсов. Анализ по подразделениям/исполнителям может быть нестабильным.",
            n_cases))
    else:
        checks.append(HealthCheck('cases_count', 'info',
            f"{n_cases} кейсов — достаточно для надёжного анализа.", n_cases))
    
    # 2. Среднее число событий на кейс
    avg_events_per_case = n_events / n_cases
    if avg_events_per_case < 3:
        checks.append(HealthCheck('events_per_case', 'warning',
            f"Среднее число операций на кейс — {avg_events_per_case:.1f}. "
            "Слишком мало для содержательного анализа последовательностей.",
            avg_events_per_case))
    else:
        checks.append(HealthCheck('events_per_case', 'info',
            f"Среднее число операций на кейс: {avg_events_per_case:.1f}",
            avg_events_per_case))
    
    # 3. Глобальный rework
    rework_pct = compute_global_rework_pct(df)
    if rework_pct < 5:
        checks.append(HealthCheck('rework_pct', 'warning',
            f"Глобальный % повторов — {rework_pct:.1f}%. "
            "Анализ зацикленностей может не дать значимых результатов.",
            rework_pct))
    
    # 4. Наличие поля department
    if 'department' not in df.columns or df['department'].isna().all():
        checks.append(HealthCheck('department_field', 'warning',
            "Поле подразделения не замаплено. Анализ по ролям и SLA по подразделениям недоступен.",
            None))
    
    # 5. Наличие поля resource
    if 'resource' not in df.columns or df['resource'].isna().all():
        checks.append(HealthCheck('resource_field', 'warning',
            "Поле исполнителя не замаплено. Анализ по сотрудникам недоступен.",
            None))
    
    # Итоговый статус
    has_error = any(c.severity == 'error' for c in checks)
    has_warning = any(c.severity == 'warning' for c in checks)
    if has_error:
        status = 'poor'
    elif has_warning:
        status = 'warning'
    else:
        status = 'good'
    
    return HealthReport(status=status, checks=checks)
```

## Модуль `domain/mining/role_mapping.py` — Роли

### Авто-предложение маппинга

```python
def suggest_role_mapping(
    departments: list[str],
    global_templates: list[GlobalRoleTemplate],
) -> dict[str, str]:
    """
    Для каждого подразделения из списка пытается найти подходящую базовую роль
    по паттернам в global_templates. Не найденные → "Не размечено".
    
    global_templates: [
        {"role_name": "Юридическое управление", 
         "patterns": ["Юридическое управление", "Юр.управление", "ЮУ"]},
        {"role_name": "Финансовый блок",
         "patterns": ["Финансовое управление", "Отдел финансового планирования", 
                      "Казначей"]},
        ...
    ]
    """
    suggestions = {}
    for dept in departments:
        matched_role = None
        for template in global_templates:
            for pattern in template['patterns']:
                if pattern.lower() in dept.lower():
                    matched_role = template['role_name']
                    break
            if matched_role:
                break
        suggestions[dept] = matched_role or 'Не размечено'
    return suggestions
```

### Базовый набор ролей по умолчанию

В системе предустановлен глобальный шаблон ролей (можно редактировать админу):

```python
DEFAULT_ROLE_TEMPLATES = [
    {"role_name": "Инициатор", "patterns": []},  # дефолт, ничего не сопоставляется
    {"role_name": "Юридическое управление", "patterns": [
        "Юридическое управление", "Юр.управление", "ЮУ", 
        "правовой поддержки"
    ]},
    {"role_name": "Финансовый блок", "patterns": [
        "Финансовое управление", "Отдел финансового планирования",
        "ОФП", "Казначей", "казначейск"
    ]},
    {"role_name": "Бухгалтерия", "patterns": [
        "бухгалтерского учета", "Бухгалтер", "налогооблож"
    ]},
    {"role_name": "Экономическая безопасность", "patterns": [
        "экономической безопасности"
    ]},
    {"role_name": "Закупки", "patterns": [
        "Управление закупок", "Отдел планирования и организации закупок",
        "закупок"
    ]},
    {"role_name": "Договорной отдел", "patterns": [
        "Договорной отдел"
    ]},
    {"role_name": "Высшее руководство", "patterns": [
        "Генеральный директор", "Заместитель генерального"
    ]},
    {"role_name": "Документооборот", "patterns": [
        "документационного обеспечения", "организационного обеспечения"
    ]},
    {"role_name": "Информационная безопасность", "patterns": [
        "информационной безопасности", "корпоративной защиты"
    ]},
]
```

### Применение маппинга к event log

```python
def apply_role_mapping(
    df: pd.DataFrame,
    role_mapping: dict[str, str],
) -> pd.DataFrame:
    """
    Создаёт новые колонки:
      - role: маппинг department → role (через role_mapping)
      - activity_with_role: переписанное название операции с заменой 
                            "Согласование Х" → "Согласование <роль_Х>"
    
    Логика переименования activity:
      Если в activity встречается подразделение из role_mapping,
      и его роль ≠ имя подразделения, заменяем имя подразделения на роль.
    
    Пример:
      activity = "Согласование Проект 001"
      role_mapping = {"Проект 001": "Инициатор"}
      → activity_with_role = "Согласование Инициатор"
    
    Возвращает df с добавленными колонками. activity (исходная) сохраняется!
    """
    result = df.copy()
    
    # role: маппинг department → role
    result['role'] = result['department'].map(role_mapping).fillna('Не размечено')
    
    # activity_with_role: переписываем имя операции
    def remap_activity(activity, department):
        if pd.isna(department):
            return activity
        role = role_mapping.get(department, 'Не размечено')
        if role == department:
            return activity  # имя совпадает, ничего не меняем
        # Пытаемся заменить department в activity на role
        if department in activity:
            return activity.replace(department, role)
        return activity
    
    result['activity_with_role'] = result.apply(
        lambda r: remap_activity(r['activity'], r['department']), axis=1
    )
    
    return result
```

### Drill-down: какие сырые имена входят в одну роль/операцию

```python
def get_activity_breakdown(
    df_with_roles: pd.DataFrame,
    activity_with_role: str,
) -> pd.DataFrame:
    """
    Для заданной роль-операции возвращает список исходных (сырых) имён операций
    с количеством событий по каждому.
    
    Используется в UI для drill-down при клике на узел графа.
    """
    mask = df_with_roles['activity_with_role'] == activity_with_role
    breakdown = (df_with_roles[mask]
                 .groupby('activity')
                 .agg(events=('case_id', 'count'),
                      cases=('case_id', 'nunique'))
                 .reset_index()
                 .sort_values('events', ascending=False))
    return breakdown
```

## Модуль `domain/mining/duration.py` — Длительности

### Sojourn time (длительность с учётом перехода)

**Это ключевая метрика длительности в process mining.** Используется в большинстве отчётов Газпрома.

```python
def compute_sojourn_time(df: pd.DataFrame) -> pd.DataFrame:
    """
    Добавляет колонку 'sojourn_seconds' в df.
    
    Алгоритм:
      Для каждого события в кейсе:
        sojourn = timestamp_end - timestamp_end_предыдущего_события_в_этом_кейсе
        Для первого события в кейсе: sojourn = own_duration (timestamp_end - timestamp_start)
    
    Сортировка внутри кейса — по timestamp_end, затем по timestamp_start (стабильно).
    """
    result = df.sort_values(['case_id', 'timestamp_end', 'timestamp_start']).reset_index(drop=True)
    
    result['prev_end'] = result.groupby('case_id')['timestamp_end'].shift(1)
    result['sojourn_seconds'] = (
        result['timestamp_end'] - result['prev_end']
    ).dt.total_seconds()
    
    # Для первого события в кейсе
    first_mask = result['prev_end'].isna()
    result.loc[first_mask, 'sojourn_seconds'] = (
        result.loc[first_mask, 'timestamp_end'] - result.loc[first_mask, 'timestamp_start']
    ).dt.total_seconds()
    
    result.drop(columns=['prev_end'], inplace=True)
    return result
```

### Собственная длительность операции

```python
def compute_own_duration(df: pd.DataFrame) -> pd.Series:
    """own_duration_seconds = timestamp_end - timestamp_start"""
    return (df['timestamp_end'] - df['timestamp_start']).dt.total_seconds()
```

### Длительность кейса

```python
def compute_case_duration(df: pd.DataFrame) -> pd.DataFrame:
    """
    Для каждого кейса:
      duration = max(timestamp_end) - min(timestamp_start)
    
    Возвращает DataFrame: case_id | start | end | duration_seconds | n_events | n_unique_activities
    """
    return df.groupby('case_id').agg(
        start=('timestamp_start', 'min'),
        end=('timestamp_end', 'max'),
        n_events=('activity', 'count'),
        n_unique_activities=('activity', 'nunique'),
    ).assign(
        duration_seconds=lambda x: (x['end'] - x['start']).dt.total_seconds()
    ).reset_index()
```

### Длительность в рабочих vs календарных днях

```python
from workalendar.europe import Russia

class WorkdayCalculator:
    def __init__(self, country: str = 'RU'):
        self.cal = Russia()  # производственный календарь РФ
    
    def calendar_seconds(self, start: datetime, end: datetime) -> float:
        """Простая разница в секундах."""
        return (end - start).total_seconds()
    
    def working_seconds(self, start: datetime, end: datetime,
                       work_day_start: time = time(9, 0),
                       work_day_end: time = time(18, 0)) -> float:
        """
        Рабочее время между двумя datetime.
        Учитываются только: понедельник-пятница (исключая праздники РФ), 
        часы work_day_start..work_day_end.
        
        Алгоритм:
          1. Если start или end вне рабочих часов — сдвигаем к ближайшим рабочим.
          2. Идём по дням от start.date() до end.date():
             - Если рабочий день: добавляем пересечение [day_start, day_end] с [start, end]
             - Если выходной/праздник: пропускаем
          3. Возвращаем сумму секунд.
        """
        # ... реализация (есть готовая в workalendar или пишется ~50 строк)
        ...
    
    def is_working_day(self, dt: date) -> bool:
        return self.cal.is_working_day(dt)
```

**Важно:** для корректного расчёта рабочих часов все timestamps должны конвертироваться в МСК (Europe/Moscow) перед вызовом `working_seconds`. В БД хранятся в UTC, при расчёте — приводим к МСК.

## Модуль `domain/mining/rework.py` — Анализ повторов (ping-pong)

### Основная функция

```python
def compute_rework_per_operation(df: pd.DataFrame) -> pd.DataFrame:
    """
    Воспроизводит таблицу со слайдов 7, 12, 17, 24 отчёта Газпрома.
    
    Алгоритм:
      1. Группируем по (case_id, activity), считаем cnt.
      2. repeats = cnt - 1 для каждой группы (если cnt > 1).
      3. Агрегируем по activity:
         total = SUM(cnt)
         repeats = SUM(repeats)
         rework_pct = repeats / total * 100
    
    Возвращает DataFrame: activity | total | repeats | rework_pct
    Сортировка по total DESC.
    """
    per_case_op = df.groupby(['case_id', 'activity']).size().reset_index(name='cnt')
    per_case_op['repeats'] = (per_case_op['cnt'] - 1).clip(lower=0)
    
    agg = per_case_op.groupby('activity').agg(
        total=('cnt', 'sum'),
        repeats=('repeats', 'sum'),
    ).reset_index()
    agg['rework_pct'] = (agg['repeats'] / agg['total'] * 100).round(2)
    
    return agg.sort_values('total', ascending=False).reset_index(drop=True)
```

### Глобальный процент rework

```python
def compute_global_rework_pct(df: pd.DataFrame) -> float:
    """
    Общий процент повторов по всему датасету.
    = SUM(repeats) / SUM(total) * 100
    """
    rework_df = compute_rework_per_operation(df)
    total = rework_df['total'].sum()
    repeats = rework_df['repeats'].sum()
    return round(repeats / total * 100, 2) if total > 0 else 0.0
```

### Кейсы с повторами vs без

```python
def split_cases_by_rework(df: pd.DataFrame) -> tuple[set[str], set[str]]:
    """
    Возвращает (cases_with_rework, cases_without_rework).
    Кейс имеет повтор, если хотя бы одна операция в нём встретилась >1 раз.
    """
    case_stats = df.groupby('case_id').agg(
        n_events=('activity', 'count'),
        n_unique=('activity', 'nunique'),
    )
    case_stats['has_rework'] = case_stats['n_events'] > case_stats['n_unique']
    
    with_rework = set(case_stats[case_stats['has_rework']].index)
    without_rework = set(case_stats[~case_stats['has_rework']].index)
    return with_rework, without_rework


def compute_duration_comparison(df: pd.DataFrame) -> dict:
    """
    Воспроизводит KPI-карточки "С повторами / Без повторов" со слайдов 7, 12, 17.
    """
    case_dur = compute_case_duration(df)
    with_rework, without_rework = split_cases_by_rework(df)
    
    avg_with = case_dur[case_dur['case_id'].isin(with_rework)]['duration_seconds'].mean()
    avg_without = case_dur[case_dur['case_id'].isin(without_rework)]['duration_seconds'].mean()
    
    return {
        'avg_duration_with_rework_seconds': float(avg_with) if not pd.isna(avg_with) else None,
        'avg_duration_without_rework_seconds': float(avg_without) if not pd.isna(avg_without) else None,
        'n_cases_with_rework': len(with_rework),
        'n_cases_without_rework': len(without_rework),
    }
```

**Golden test эталоны** (на synthetic_log.xlsx):
- Глобальный rework: **20.06%**
- Кейсов с повторами: **1145**
- Кейсов без повторов: **183**
- Средняя длительность с повторами: **~22.05 дней**
- Средняя длительность без повторов: **~11.79 дней**
- Топ-3 операции по объёму: "Проверка Договорной отдел" (1717/total), "Подготовка к подписанию Договорной отдел" (1633), "Дополнительное согласование Отдел финансового планирования и отчетности" (1450)

## Модуль `domain/mining/variants.py` — Варианты процесса и пути

### Трасса кейса

```python
def get_case_traces(df: pd.DataFrame) -> pd.Series:
    """
    Для каждого кейса — кортеж операций в хронологическом порядке.
    
    Сортировка внутри кейса: по timestamp_start, затем по timestamp_end (стабильно).
    
    Возвращает Series: index=case_id, value=tuple[str, ...]
    """
    return (df.sort_values(['case_id', 'timestamp_start', 'timestamp_end'])
              .groupby('case_id')['activity']
              .apply(tuple))
```

### ТОП-N путей процесса

```python
def get_top_n_variants(df: pd.DataFrame, n: int = 5) -> pd.DataFrame:
    """
    Воспроизводит слайд 9, 14, 19 отчёта Газпрома.
    
    Возвращает DataFrame с топ-N уникальных трасс:
      trace (tuple) | n_cases | avg_duration_seconds | example_case_ids
    
    Сортировка по n_cases DESC.
    """
    traces = get_case_traces(df)
    case_dur = compute_case_duration(df).set_index('case_id')
    
    variants = []
    for trace, case_ids in traces.groupby(traces).groups.items():
        cases_list = list(case_ids)
        avg_dur = case_dur.loc[cases_list, 'duration_seconds'].mean()
        variants.append({
            'trace': trace,
            'n_cases': len(cases_list),
            'avg_duration_seconds': float(avg_dur),
            'example_case_ids': cases_list[:5],  # для drill-down
        })
    
    variants_df = pd.DataFrame(variants).sort_values('n_cases', ascending=False)
    return variants_df.head(n).reset_index(drop=True)


def get_variants_coverage(df: pd.DataFrame, n: int = 5) -> dict:
    """
    Сколько кейсов покрывают топ-N путей.
    Для слайда 9: "ТОП-5 путей покрывают 84 из 1316 экземпляров"
    """
    traces = get_case_traces(df)
    total_cases = len(traces)
    total_variants = traces.nunique()
    
    top_n_variants = get_top_n_variants(df, n=n)
    covered = int(top_n_variants['n_cases'].sum())
    
    return {
        'total_cases': total_cases,
        'total_variants': total_variants,
        'top_n': n,
        'covered_cases': covered,
        'coverage_pct': round(covered / total_cases * 100, 2),
    }
```

### Метрики вариативности и встречаемости

```python
def compute_variability_pct(df: pd.DataFrame) -> float:
    """
    Воспроизводит метрику слайда 21 ЗНИ Газпрома: 18.4% для ЗНИ.
    
    variability = unique_traces / total_cases * 100
    Чем ниже, тем стандартизованнее процесс.
    """
    traces = get_case_traces(df)
    return round(traces.nunique() / len(traces) * 100, 2) if len(traces) > 0 else 0.0


def compute_mean_occurrence_pct(df: pd.DataFrame) -> float:
    """
    Воспроизводит метрику слайда 21 ЗНИ Газпрома: 25.91% для ЗНИ.
    
    Для каждой операции считаем % кейсов, в которых она встретилась.
    Возвращаем среднее по всем операциям.
    Высокое значение = большинство операций встречаются часто (мало "редких").
    """
    total_cases = df['case_id'].nunique()
    op_freq = df.groupby('activity')['case_id'].nunique() / total_cases * 100
    return round(float(op_freq.mean()), 2) if len(op_freq) > 0 else 0.0
```

**Golden test эталоны** (synthetic_log.xlsx):
- variability_pct: **89.83%** (процесс крайне вариативный)
- mean_occurrence_pct: **3.04%** (типичная операция встречается лишь в 3% кейсов)

## Модуль `domain/mining/graph.py` — Графы процессов

### Directly-Follows Graph (DFG)

```python
@dataclass
class DFGEdge:
    from_activity: str
    to_activity: str
    count: int          # сколько раз встретился этот переход
    avg_duration_seconds: float  # средняя длительность перехода

@dataclass
class DFGNode:
    activity: str
    count: int          # сколько раз встретилась эта операция
    avg_own_duration_seconds: float

@dataclass
class DFG:
    nodes: list[DFGNode]
    edges: list[DFGEdge]
    start_activities: dict[str, int]  # активности-старты, по кейсам
    end_activities: dict[str, int]    # активности-концы, по кейсам


def build_dfg(df: pd.DataFrame, activity_col: str = 'activity') -> DFG:
    """
    Строит Directly-Follows Graph.
    
    Алгоритм:
      Сортируем df по (case_id, timestamp_start).
      Для каждой пары последовательных строк в одном кейсе создаём ребро.
      Агрегируем по (from, to).
    
    activity_col — либо 'activity' (сырые имена), либо 'activity_with_role' (свёрнутые).
    """
    df_sorted = df.sort_values(['case_id', 'timestamp_start', 'timestamp_end'])
    df_sorted['next_activity'] = df_sorted.groupby('case_id')[activity_col].shift(-1)
    df_sorted['next_start'] = df_sorted.groupby('case_id')['timestamp_start'].shift(-1)
    df_sorted['transition_duration'] = (
        df_sorted['next_start'] - df_sorted['timestamp_end']
    ).dt.total_seconds()
    
    # Edges
    edges_df = df_sorted[df_sorted['next_activity'].notna()].groupby(
        [activity_col, 'next_activity']
    ).agg(
        count=('case_id', 'count'),
        avg_duration=('transition_duration', 'mean'),
    ).reset_index()
    edges = [
        DFGEdge(row[activity_col], row['next_activity'], 
                int(row['count']), float(row['avg_duration']))
        for _, row in edges_df.iterrows()
    ]
    
    # Nodes
    nodes_df = df_sorted.groupby(activity_col).agg(
        count=('case_id', 'count'),
        avg_own_dur=('own_duration_sec', 'mean'),
    ).reset_index()
    nodes = [
        DFGNode(row[activity_col], int(row['count']), float(row['avg_own_dur']))
        for _, row in nodes_df.iterrows()
    ]
    
    # Старты и концы
    starts = df_sorted.groupby('case_id').first()[activity_col].value_counts().to_dict()
    ends = df_sorted.groupby('case_id').last()[activity_col].value_counts().to_dict()
    
    return DFG(nodes=nodes, edges=edges, start_activities=starts, end_activities=ends)
```

### Фильтрация графа

```python
def filter_dfg(
    dfg: DFG,
    min_edge_frequency_pct: float = 0,
    top_n_paths: int | None = None,
) -> DFG:
    """
    Возвращает упрощённый граф:
      - min_edge_frequency_pct: удалить рёбра с count < N% от max(count)
      - top_n_paths: оставить только узлы и рёбра, входящие в топ-N путей процесса
    
    Обе фильтрации можно применять последовательно.
    """
    ...
```

### BPMN-экспорт

```python
def dfg_to_bpmn(dfg: DFG) -> str:
    """
    Конвертирует DFG в BPMN 2.0 XML.
    
    Стратегия:
      - Каждая операция → BPMN Task
      - Каждое ребро → SequenceFlow
      - Starts → StartEvent + потоки в первые активности
      - Ends → EndEvent + потоки из последних активностей
      - Никакого conformance, просто визуальное представление
    
    Используется bpmn-python библиотека или ручная генерация XML.
    """
    ...
```

## Модуль `domain/mining/sla.py` — SLA-комплаенс

### Оценка одной операции против SLA

```python
def evaluate_operation_sla(
    sojourn_seconds: float,
    sla_rule: SLARule,
    calculator: WorkdayCalculator,
    start_time: datetime,
) -> SLAEvaluation:
    """
    Проверяет: укладывается ли операция в SLA.
    
    Логика:
      1. Конвертируем sla_value в секунды согласно sla_unit:
         - workdays: считаем рабочие секунды от start_time на sla_value рабочих дней
         - calendar_days: sla_value * 86400
         - workhours: считаем рабочие секунды на sla_value часов
         - hours: sla_value * 3600
      2. Добавляем tolerance_hours.
      3. Сравниваем sojourn_seconds с порогом.
    
    Возвращает SLAEvaluation(passed: bool, threshold_seconds: float, excess_seconds: float).
    """
    ...

def evaluate_sla_compliance(
    df_with_sojourn: pd.DataFrame,  # с колонкой sojourn_seconds + role
    sla_rules: list[SLARule],
    calculator: WorkdayCalculator,
) -> pd.DataFrame:
    """
    Для каждого события находит подходящее SLA-правило (по role + activity match)
    и проверяет, прошло ли SLA.
    
    Возвращает df + колонки: sla_threshold_seconds, sla_passed (bool), 
                             matched_rule_id (int | None)
    
    Если правило не найдено: sla_passed = NULL (не учитываем в статистике).
    """
    ...

def aggregate_sla_compliance(df_with_sla: pd.DataFrame) -> pd.DataFrame:
    """
    Воспроизводит таблицу SLA-PDF Газпрома.
    
    Группировка по activity:
      total_events | total_with_sla | passed | failed | pass_pct
    """
    ...
```

### Поиск SLA-правила для операции (match logic)

```python
def find_matching_rule(
    activity: str,
    role: str,
    rules: list[SLARule],
) -> SLARule | None:
    """
    Приоритет правил:
      1. Точное совпадение activity И role
      2. activity = '*' И точное role
      3. Точное activity И role = '*'
      4. activity = '*' И role = '*'
    
    Возвращает первое подходящее правило (по эффективной дате тоже фильтруем).
    """
    ...
```

## Модуль `domain/mining/resources.py` — Анализ исполнителей

```python
def compute_resource_workload(df: pd.DataFrame) -> pd.DataFrame:
    """
    Для каждого исполнителя:
      n_cases (уникальных кейсов с участием)
      n_events (всего операций)
      avg_own_duration_seconds (среднее собственное время операции)
      n_unique_activities (сколько разных операций выполнял)
    
    Возвращает DataFrame: resource | n_cases | n_events | avg_own_duration_sec | n_unique_activities
    Сортировка по n_events DESC.
    """
    return df.groupby('resource').agg(
        n_cases=('case_id', 'nunique'),
        n_events=('activity', 'count'),
        avg_own_duration_seconds=('own_duration_sec', 'mean'),
        n_unique_activities=('activity', 'nunique'),
    ).reset_index().sort_values('n_events', ascending=False)
```

## Модуль `domain/mining/dynamics.py` — Динамика по месяцам

```python
def compute_monthly_dynamics(
    df: pd.DataFrame,
    activity_filter: str | None = None,
) -> pd.DataFrame:
    """
    Воспроизводит графики "Количество операций + Средняя длительность с учётом перехода"
    со слайдов 6, 11, 16, 21, 22.
    
    Если activity_filter задан — фильтруем только эту операцию (как на слайде 23: одна операция).
    
    Группировка по месяцу (по timestamp_start).
    
    Возвращает: month (str YYYY-MM) | n_events | avg_sojourn_seconds | n_cases
    """
    work = df.copy()
    if activity_filter:
        work = work[work['activity'] == activity_filter]
    
    if 'sojourn_seconds' not in work.columns:
        work = compute_sojourn_time(work)
    
    work['month'] = work['timestamp_start'].dt.tz_convert('Europe/Moscow').dt.to_period('M').astype(str)
    
    result = work.groupby('month').agg(
        n_events=('activity', 'count'),
        avg_sojourn_seconds=('sojourn_seconds', 'mean'),
        n_cases=('case_id', 'nunique'),
    ).reset_index().sort_values('month')
    
    return result
```

## Модуль `domain/mining/filters.py` — Фильтрация

```python
@dataclass
class EventFilter:
    date_range: tuple[datetime, datetime] | None = None
    departments: list[str] | None = None
    roles: list[str] | None = None
    resources: list[str] | None = None
    activities: list[str] | None = None
    case_duration_range: tuple[float, float] | None = None  # секунды
    with_rework: bool | None = None  # None=все, True=только с повторами, False=без
    attributes_filter: dict[str, list[str]] | None = None  # {"doc_type": ["Договорный"]}
    case_ids: list[str] | None = None

def apply_filter(df: pd.DataFrame, f: EventFilter) -> pd.DataFrame:
    """
    Применяет фильтр к event log.
    
    Важно: фильтр по case_duration_range и with_rework — это фильтры НА КЕЙС,
    а не на отдельное событие. Если кейс попадает под фильтр, остаются ВСЕ
    его события, чтобы не порушить трассу.
    """
    result = df
    
    if f.date_range:
        start, end = f.date_range
        result = result[(result['timestamp_start'] >= start) & (result['timestamp_start'] <= end)]
    
    if f.departments:
        result = result[result['department'].isin(f.departments)]
    
    if f.roles and 'role' in result.columns:
        result = result[result['role'].isin(f.roles)]
    
    # ... и так далее
    
    # Фильтры на уровне кейса
    if f.with_rework is not None or f.case_duration_range:
        case_dur = compute_case_duration(result)
        with_rework_set, without_rework_set = split_cases_by_rework(result)
        
        if f.with_rework is True:
            valid_cases = with_rework_set
        elif f.with_rework is False:
            valid_cases = without_rework_set
        else:
            valid_cases = set(case_dur['case_id'])
        
        if f.case_duration_range:
            min_d, max_d = f.case_duration_range
            duration_mask = (case_dur['duration_seconds'] >= min_d) & \
                            (case_dur['duration_seconds'] <= max_d)
            valid_cases &= set(case_dur[duration_mask]['case_id'])
        
        result = result[result['case_id'].isin(valid_cases)]
    
    return result
```

## Общие принципы для всех алгоритмов

1. **Чистые функции.** Все функции принимают DataFrame, возвращают DataFrame/dict/dataclass. Никаких side effects, никаких обращений к БД внутри.
2. **Pandas как основа.** Расчёты в pandas, потом сериализация в Pydantic-схемы для API.
3. **pm4py для сложного.** Алгоритмы process discovery (Inductive, Heuristic Miner) берём готовые из pm4py. DFG, базовые метрики — пишем сами для контроля.
4. **Время — UTC внутри, МСК на границе.** В pandas работаем в UTC. При выводе в UI — конвертируем в МСК. Для расчёта рабочих часов — приводим к МСК.
5. **Кэширование тяжёлых расчётов.** Расчёт `cached_stats` виртуального датасета — в фоне через Celery. Результат — в JSONB-поле.

## Привязка к golden tests

См. `06_TESTING.md` — каждый алгоритм покрыт тестом, проверяющим, что на `golden_data/synthetic_log.xlsx` он возвращает значения из `golden_data/expected_metrics.json` (с tolerance 1% для float).

## Что читать дальше

- API-эндпоинты, использующие эти алгоритмы → `03_API.md`
- Визуализация результатов в UI → `04_UI.md`
- Тесты на алгоритмы → `06_TESTING.md`
