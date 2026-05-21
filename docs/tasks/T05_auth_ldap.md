# T05: LDAP-логин (опциональный)

## Цель
Добавить вход через LDAP/AD. Принцип: "залогиниться через AD, дальше работать локально".

## Контекст
- `00_OVERVIEW.md` — упоминание LDAP
- `05_INFRA.md` раздел "Конфигурация" — переменные LDAP_*
- `T04_auth_local.md` — базовая аутентификация

## DoD
- [ ] `app/services/ldap_service.py` с функцией `authenticate_ldap(username, password) -> LdapUserInfo | None`.
- [ ] Эндпоинт `POST /api/v1/auth/login` поддерживает поле `use_ldap: bool` в request.
- [ ] При первом успешном LDAP-входе автоматически создаётся локальный user с `is_ldap=True`, `password_hash=NULL`. При следующих входах — обновляется `last_login_at`.
- [ ] LDAP отключён по умолчанию (`LDAP_ENABLED=false`); при попытке LDAP-логина и `LDAP_ENABLED=false` → 503.
- [ ] Роль нового LDAP-пользователя — всегда `analyst` (админ должен повысить вручную).
- [ ] Тесты с моком LDAP-сервера.

## Реализация

### `app/services/ldap_service.py`
```python
from ldap3 import Server, Connection, ALL, SUBTREE, SAFE_SYNC
from dataclasses import dataclass
from app.core.config import settings

@dataclass
class LdapUserInfo:
    username: str
    full_name: str | None
    email: str | None

def authenticate_ldap(username: str, password: str) -> LdapUserInfo | None:
    if not settings.LDAP_ENABLED:
        return None
    
    server = Server(settings.LDAP_SERVER, get_info=ALL)
    
    # Сначала bind с service account для поиска пользователя
    try:
        conn = Connection(
            server,
            user=settings.LDAP_BIND_DN,
            password=settings.LDAP_BIND_PASSWORD,
            client_strategy=SAFE_SYNC,
            auto_bind=True,
        )
    except Exception:
        return None
    
    search_filter = settings.LDAP_USER_SEARCH_FILTER.format(username=username)
    conn.search(
        settings.LDAP_USER_SEARCH_BASE,
        search_filter,
        SUBTREE,
        attributes=['displayName', 'mail', 'sAMAccountName'],
    )
    
    if not conn.entries:
        return None
    
    user_dn = conn.entries[0].entry_dn
    entry = conn.entries[0]
    
    # Bind с найденным DN + введённым паролем для проверки
    try:
        Connection(server, user=user_dn, password=password, auto_bind=True)
    except Exception:
        return None
    
    return LdapUserInfo(
        username=username,
        full_name=str(entry.displayName) if 'displayName' in entry else None,
        email=str(entry.mail) if 'mail' in entry else None,
    )
```

### Изменения в `auth_service.py`
В `login()`:
```python
if request.use_ldap:
    if not settings.LDAP_ENABLED:
        raise ServiceUnavailable("LDAP not configured")
    ldap_info = authenticate_ldap(request.username, request.password)
    if not ldap_info:
        raise InvalidCredentials()
    
    # Find or create local user
    user = await db.scalar(select(User).where(User.username == ldap_info.username))
    if not user:
        user = User(
            username=ldap_info.username,
            full_name=ldap_info.full_name,
            email=ldap_info.email,
            is_ldap=True,
            password_hash=None,
            role="analyst",
            is_active=True,
        )
        db.add(user)
        await db.flush()
    
    # ... остальное как обычно (создание токенов)
```

## Тесты
- `test_ldap_login_success_creates_user` (с моком ldap3).
- `test_ldap_login_wrong_password` → 401.
- `test_ldap_disabled_returns_503`.
- `test_ldap_login_existing_user_updates_last_login`.

## Acceptance
Если в .env установлены LDAP_* и LDAP_ENABLED=true, можно сделать POST /login с use_ldap=true и реальными AD-credentials, получить токены, и в auth.users появится запись с is_ldap=true.
