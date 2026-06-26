"""T41 — каркас вкладочного дашборда.

Покрытие: каждая запись в `_DEFAULT_WIDGETS` имеет валидный `tab`, листающий
один из ключей `STANDARD_PM_TAB_KEYS`. Это страховка от рассинхрона между
backend-таксономией вкладок и значениями `tab` в виджетах по умолчанию.
"""
from app.services.dashboard_service import (
    _DEFAULT_WIDGETS,
    _OVERVIEW_WIDGETS,
    _PROCESS_WIDGETS,
    STANDARD_PM_TAB_KEYS,
)


def test_default_widgets_all_have_valid_tab() -> None:
    allowed = set(STANDARD_PM_TAB_KEYS)
    for widget in _DEFAULT_WIDGETS:
        assert "tab" in widget, f"виджет '{widget['title']}' без tab"
        assert widget["tab"] in allowed, (
            f"виджет '{widget['title']}' имеет tab='{widget['tab']}', "
            f"которой нет в STANDARD_PM_TAB_KEYS"
        )


def test_tab_keys_unique() -> None:
    assert len(set(STANDARD_PM_TAB_KEYS)) == len(STANDARD_PM_TAB_KEYS), (
        "ключи вкладок не уникальны"
    )


def test_tab_keys_cover_required_structure() -> None:
    """REQ §6.7: 4 топ-вкладки и фиксированный набор подвкладок."""
    keys = set(STANDARD_PM_TAB_KEYS)
    assert "standard_metrics" in keys
    assert "overview" in keys
    # Процесс — 5 подвкладок
    for sub in ("process", "duration", "rework", "paths", "distribution"):
        assert f"process.{sub}" in keys, f"нет process.{sub}"
    # Детали — 3 подвкладки
    for sub in ("cases", "operations", "dataset"):
        assert f"details.{sub}" in keys, f"нет details.{sub}"


def test_overview_widgets_all_on_overview_tab() -> None:
    """T41.1: все виджеты вкладки «Обзор» помечены tab='overview'."""
    assert _OVERVIEW_WIDGETS, "набор overview-виджетов пуст"
    for widget in _OVERVIEW_WIDGETS:
        assert widget["tab"] == "overview", (
            f"виджет '{widget['title']}' имеет tab='{widget['tab']}', ожидался overview"
        )


def test_overview_layout_matches_sketch() -> None:
    """T41.3: ключевые элементы согласованного эскиза присутствуют.

    13 виджетов; динамика по месяцам 3/4 ширины × h=11 (нижний край точно
    совпадает с нижним краем последнего KPI «Встречаемость» на строке 13);
    столбик из 4 KPI справа распределён по y=2,5,8,11; нижние ряды
    y=14 (гистограмма/поток) и y=19 (повторы/пути), по половине ширины.
    """
    assert len(_OVERVIEW_WIDGETS) == 13

    by_title = {w["title"]: w for w in _OVERVIEW_WIDGETS}

    dynamics = by_title["Динамика по месяцам"]
    assert dynamics["widget_type"] == "monthly_dynamics"
    assert dynamics["grid_x"] == 0 and dynamics["grid_width"] == 9
    assert dynamics["grid_height"] == 11, "T41.3: динамика должна быть h=11"

    # Столбик из 4 KPI справа — в колонке x=9, равномерно распределён.
    right_stack = ["Начало процесса", "Конец процесса",
                   "Вариативность путей", "Встречаемость операций"]
    ys = []
    for title in right_stack:
        w = by_title[title]
        assert w["grid_x"] == 9 and w["grid_width"] == 3 and w["grid_height"] == 2
        ys.append(w["grid_y"])
    assert ys == [2, 5, 8, 11], (
        f"T41.3: KPI справа должны идти по y=2,5,8,11, получили {ys}"
    )

    # T41.3: нижний край динамики (y+h=13) совпадает с нижним краем последнего KPI.
    last_kpi = by_title["Встречаемость операций"]
    assert (
        dynamics["grid_y"] + dynamics["grid_height"]
        == last_kpi["grid_y"] + last_kpi["grid_height"]
    ), "T41.3: низ динамики и низ последнего KPI должны совпадать"

    # Нижние ряды — половинная ширина, опущены под динамику h=11.
    for title in ("Кол-во операций в экземпляре", "Входящий и исходящий поток"):
        w = by_title[title]
        assert w["grid_width"] == 6 and w["grid_y"] == 14
    for title in ("Топ повторов", "Топ-5 путей процесса"):
        w = by_title[title]
        assert w["grid_width"] == 6 and w["grid_y"] == 19

    # Виджеты «Топ повторов» и «Топ путей» используют ожидаемые типы.
    assert by_title["Топ повторов"]["widget_type"] == "rework_table"
    assert by_title["Топ-5 путей процесса"]["widget_type"] == "top_paths_graph"


def test_process_subtabs_have_default_widgets() -> None:
    """T47/T45: дефолтные виджеты на process.rework, process.distribution и
    process.duration (boxplot длительности операций, добавлен в T45).
    На process.process рендерится богатый ProcessGraphTab (embedded) на фронте —
    виджет в БД ему не нужен. process.paths остаётся пустым."""
    expected_tabs = {"process.rework", "process.distribution", "process.duration"}
    covered = {w["tab"] for w in _PROCESS_WIDGETS}
    assert covered == expected_tabs, (
        f"T45/T47: ожидаем rework, distribution и duration; получили {covered}"
    )


def test_process_duration_has_boxplot() -> None:
    """T45: на process.duration лежит виджет «ящик с усами» с дефолтом
    limit=15 и activity_level='raw'."""
    [boxplot] = [
        w for w in _PROCESS_WIDGETS if w["tab"] == "process.duration"
    ]
    assert boxplot["widget_type"] == "operation_durations_boxplot"
    assert boxplot["config"]["limit"] == 15
    assert boxplot["config"]["activity_level"] == "raw"
    assert boxplot["grid_width"] == 12


def test_default_widgets_count() -> None:
    """T45: 13 overview + 3 process (rework, distribution, duration-boxplot)
    + 1 details = 17 виджетов."""
    assert len(_DEFAULT_WIDGETS) == 17
