#!/usr/bin/env python3
"""Проверяет целостность каталога бэкапа (см. docs/tasks/T40_backup_restore.md)."""

import json
import sys
from pathlib import Path


def verify(backup_dir: Path) -> list[str]:
    """Возвращает список найденных проблем; пустой список — бэкап целостен."""
    errors: list[str] = []

    db_dump = backup_dir / "db.dump"
    if not db_dump.exists():
        errors.append("db.dump отсутствует")
    elif db_dump.stat().st_size == 0:
        errors.append("db.dump пустой")

    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.exists():
        errors.append("manifest.json отсутствует")
    else:
        try:
            json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            errors.append("manifest.json повреждён")

    if not (backup_dir / "uploads").exists():
        errors.append("каталог uploads/ отсутствует")

    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Использование: verify_backup.py <backup_dir>")
        return 1
    errors = verify(Path(sys.argv[1]))
    if errors:
        print("ОШИБКИ:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("OK: бэкап целостен")
    return 0


if __name__ == "__main__":
    sys.exit(main())
