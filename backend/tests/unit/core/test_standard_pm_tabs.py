"""T41 — каркас вкладочного дашборда.

Покрытие: каждая запись в `_DEFAULT_WIDGETS` имеет валидный `tab`, листающий
один из ключей `STANDARD_PM_TAB_KEYS`. Это страховка от рассинхрона между
backend-таксономией вкладок и значениями `tab` в виджетах по умолчанию.
"""
from app.services.dashboard_service import _DEFAULT_WIDGETS, STANDARD_PM_TAB_KEYS


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
