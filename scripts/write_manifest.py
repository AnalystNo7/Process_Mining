#!/usr/bin/env python3
"""Записывает manifest.json в каталог бэкапа (см. docs/tasks/T40_backup_restore.md)."""

import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path


def _system_version(repo_root: Path) -> str:
    pyproject = repo_root / "backend" / "pyproject.toml"
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return "unknown"
    return str(data.get("project", {}).get("version", "unknown"))


def build_manifest(backup_dir: Path, repo_root: Path) -> dict[str, object]:
    db_dump = backup_dir / "db.dump"
    uploads_dir = backup_dir / "uploads"
    upload_files = (
        [f for f in uploads_dir.rglob("*") if f.is_file()]
        if uploads_dir.exists()
        else []
    )
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "system_version": _system_version(repo_root),
        "db_dump_size_bytes": db_dump.stat().st_size if db_dump.exists() else 0,
        "uploads_files": len(upload_files),
        "uploads_size_bytes": sum(f.stat().st_size for f in upload_files),
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Использование: write_manifest.py <backup_dir>")
        return 1
    backup_dir = Path(sys.argv[1])
    repo_root = Path(__file__).resolve().parent.parent
    manifest = build_manifest(backup_dir, repo_root)
    text = json.dumps(manifest, indent=2, ensure_ascii=False)
    (backup_dir / "manifest.json").write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
