"""T46: стабильный хэш пути для идентификации вариантов процесса."""
from app.domain.mining.variants import compute_path_hash


def test_path_hash_is_16_hex_chars() -> None:
    h = compute_path_hash(["Старт", "Согласование", "Конец"])
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h), f"не hex: {h}"


def test_path_hash_stable_for_same_trace() -> None:
    """Один и тот же trace всегда даёт одинаковый hash (важно для копирования)."""
    trace = ["A", "B", "C"]
    h1 = compute_path_hash(trace)
    h2 = compute_path_hash(trace)
    h3 = compute_path_hash(tuple(trace))
    assert h1 == h2 == h3


def test_path_hash_differs_for_different_traces() -> None:
    """Разные траектории дают разные хэши (не должно быть коллизий на простых случаях)."""
    h_abc = compute_path_hash(["A", "B", "C"])
    h_acb = compute_path_hash(["A", "C", "B"])  # другой порядок
    h_ab = compute_path_hash(["A", "B"])  # короче
    assert h_abc != h_acb
    assert h_abc != h_ab
    assert h_acb != h_ab


def test_path_hash_handles_unicode() -> None:
    """Кириллица в активностях не ломает hash, имена операций — часть ключа."""
    h_ru = compute_path_hash(["Старт", "Конец"])
    h_en = compute_path_hash(["Start", "End"])
    assert h_ru != h_en
    # Регистр имеет значение — это часть имени операции.
    assert compute_path_hash(["start"]) != compute_path_hash(["Start"])


def test_path_hash_empty_trace() -> None:
    """Пустой trace тоже должен давать валидный hash (не падать)."""
    h = compute_path_hash([])
    assert len(h) == 16
