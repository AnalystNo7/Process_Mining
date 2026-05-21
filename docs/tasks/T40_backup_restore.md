# T40: Команды backup и restore

## Цель
Резервное копирование БД и загруженных файлов одной командой Makefile. Восстановление — другой командой. Без cron, без бэкап-серверов — ручное использование.

## Контекст
- `05_INFRA.md` раздел "Backup".

## DoD
- [ ] Команда `make backup` — создаёт `backups/{YYYY-MM-DD-HHMMSS}/` с:
  - `db.dump` — pg_dump в custom format (плюс схема + данные).
  - `uploads/` — копия `data/uploads/` (физические xlsx-файлы).
  - `manifest.json` — метаданные бэкапа (версия системы, дата, размер).
- [ ] Команда `make restore BACKUP_DIR=backups/2025-11-15-100000` — восстанавливает БД и файлы.
- [ ] README раздел "Backup и восстановление" с пошаговой инструкцией.
- [ ] Скрипт-валидатор `make verify-backup BACKUP_DIR=...` — проверяет целостность.

## Реализация (Makefile)
```makefile
.PHONY: backup restore verify-backup

BACKUP_DIR ?= backups/$(shell date +%Y-%m-%d-%H%M%S)

backup:
	@echo "Создаю бэкап в $(BACKUP_DIR)..."
	@mkdir -p $(BACKUP_DIR)/uploads
	@pg_dump -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME) -Fc -f $(BACKUP_DIR)/db.dump
	@cp -r data/uploads/* $(BACKUP_DIR)/uploads/ 2>/dev/null || echo "(нет файлов uploads)"
	@python scripts/write_manifest.py $(BACKUP_DIR)
	@echo "Готово. Бэкап в $(BACKUP_DIR)"

restore:
	@test -n "$(BACKUP_DIR)" || (echo "Укажите BACKUP_DIR=path/to/backup"; exit 1)
	@test -f $(BACKUP_DIR)/db.dump || (echo "$(BACKUP_DIR)/db.dump не найден"; exit 1)
	@echo "ВНИМАНИЕ! Восстановление перезапишет текущую БД '$(DB_NAME)' и uploads/!"
	@read -p "Продолжить? [y/N] " ans; [ "$$ans" = "y" ] || exit 1
	@echo "Drop & recreate БД..."
	@psql -h $(DB_HOST) -U $(DB_USER) -d postgres -c "DROP DATABASE IF EXISTS $(DB_NAME);"
	@psql -h $(DB_HOST) -U $(DB_USER) -d postgres -c "CREATE DATABASE $(DB_NAME);"
	@echo "Restore БД..."
	@pg_restore -h $(DB_HOST) -U $(DB_USER) -d $(DB_NAME) $(BACKUP_DIR)/db.dump
	@echo "Restore uploads..."
	@rm -rf data/uploads
	@cp -r $(BACKUP_DIR)/uploads data/uploads
	@echo "Готово."

verify-backup:
	@test -n "$(BACKUP_DIR)" || (echo "Укажите BACKUP_DIR="; exit 1)
	@python scripts/verify_backup.py $(BACKUP_DIR)
```

## Скрипт manifest
```python
# scripts/write_manifest.py
import sys, json, os
from datetime import datetime
from pathlib import Path

backup_dir = Path(sys.argv[1])
uploads_dir = backup_dir / "uploads"

manifest = {
    "created_at": datetime.utcnow().isoformat() + "Z",
    "system_version": "0.1.0",   # из pyproject.toml
    "db_dump_size_bytes": (backup_dir / "db.dump").stat().st_size,
    "uploads_files": len(list(uploads_dir.glob("*"))) if uploads_dir.exists() else 0,
    "uploads_size_bytes": sum(f.stat().st_size for f in uploads_dir.glob("**/*") if f.is_file()),
}
(backup_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
print(json.dumps(manifest, indent=2))
```

## Скрипт verify
```python
# scripts/verify_backup.py
import sys, json
from pathlib import Path

backup_dir = Path(sys.argv[1])
errors = []

# 1. db.dump существует и не пустой
db = backup_dir / "db.dump"
if not db.exists(): errors.append("db.dump отсутствует")
elif db.stat().st_size == 0: errors.append("db.dump пустой")

# 2. manifest.json существует и валидный JSON
manifest_path = backup_dir / "manifest.json"
if not manifest_path.exists(): errors.append("manifest.json отсутствует")
else:
    try: json.loads(manifest_path.read_text())
    except json.JSONDecodeError: errors.append("manifest.json повреждён")

# 3. uploads/ существует
uploads = backup_dir / "uploads"
if not uploads.exists(): errors.append("uploads/ отсутствует")

if errors:
    print("ОШИБКИ:")
    for e in errors: print(f"  - {e}")
    sys.exit(1)
print("OK: бэкап целостен")
```

## Документация в README
```markdown
## Резервное копирование

### Создание бэкапа

    make backup

Бэкап сохраняется в `backups/YYYY-MM-DD-HHMMSS/`.

Содержит: дамп БД (PostgreSQL), все загруженные xlsx-файлы, manifest.

### Восстановление

    make restore BACKUP_DIR=backups/2025-11-15-100000

**ВНИМАНИЕ:** восстановление сначала **удалит** текущую БД и uploads, затем восстановит из бэкапа. Используйте только когда уверены.

Перед восстановлением рекомендуется проверить целостность бэкапа:

    make verify-backup BACKUP_DIR=backups/2025-11-15-100000

### Рекомендации
- Делайте backup перед обновлением версии системы.
- Делайте backup еженедельно при активной работе.
- Храните последние 4 бэкапа, старые удаляйте вручную.
```

## Тесты
- `test_backup_creates_files` — manual: запустить `make backup`, проверить структуру каталога.
- `test_verify_backup_detects_corruption` — повредить db.dump, проверить что verify падает.
- `test_restore_roundtrip` — создать тестовый проект → backup → удалить проект → restore → проект снова виден.

## Acceptance
Сценарий roundtrip работает: создан проект с физ.датасетом → make backup → удаление проекта в UI → make restore → проект снова доступен с теми же данными.
