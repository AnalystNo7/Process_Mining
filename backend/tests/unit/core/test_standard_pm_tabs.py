"""T41 — каркас вкладочного дашборда.

Покрытие: каждая запись в `_DEFAULT_WIDGETS` имеет валидный `tab`, листающий
один из ключей `STANDARD_PM_TAB_KEYS`. Это страховка от рассинхрона между
backend-таксономией вкладок и значениями `tab` в виджетах по умолчанию.
"""
from app.services.dashboard_service import (
    _DEFAULT_WIDGETS,
    _OVERVIEW_WIDGETS,
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
    """T41.1: ключевые элементы согласованного эскиза присутствуют.

    13 виджетов; динамика по месяцам 3/4 ширины; столбик из 4 KPI справа (x=9);
    нижние ряды по половине ширины.
    """
    assert len(_OVERVIEW_WIDGETS) == 13

    by_title = {w["title"]: w for w in _OVERVIEW_WIDGETS}

    dynamics = by_title["Динамика по месяцам"]
    assert dynamics["widget_type"] == "monthly_dynamics"
    assert dynamics["grid_x"] == 0 and dynamics["grid_width"] == 9

    # Столбик из 4 KPI справа — в колонке x=9, друг под другом.
    right_stack = ["Начало процесса", "Конец процесса",
                   "Вариативность путей", "Встречаемость операций"]
    ys = []
    for title in right_stack:
        w = by_title[title]
        assert w["grid_x"] == 9 and w["grid_width"] == 3
        ys.append(w["grid_y"])
    assert ys == sorted(ys) and len(set(ys)) == 4, "карточки должны идти в столбик"

    # Нижние ряды — половинная ширина.
    for title in ("Кол-во операций в экземпляре", "Входящий и исходящий поток",
                  "Топ повторов", "Топ-5 путей процесса"):
        assert by_title[title]["grid_width"] == 6

    # Новые виджеты раскладки присутствуют.
    assert by_title["Топ повторов"]["widget_type"] == "rework_table"
    assert by_title["Топ-5 путей процесса"]["widget_type"] == "top_paths_graph"
