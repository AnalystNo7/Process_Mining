from dataclasses import dataclass

from ldap3 import ALL, SUBTREE, Connection, Server

from app.core.config import settings


@dataclass
class LdapUserInfo:
    username: str
    full_name: str | None
    email: str | None


def authenticate_ldap(username: str, password: str) -> LdapUserInfo | None:
    """Проверяет учётные данные через LDAP/AD.

    Алгоритм: bind сервисной учётной записью → поиск пользователя →
    bind под найденным DN с введённым паролём. Возвращает None при любой
    неудаче (LDAP выключен, недоступен, пользователь не найден, неверный пароль).
    """
    if not settings.LDAP_ENABLED:
        return None
    if (
        settings.LDAP_SERVER is None
        or settings.LDAP_USER_SEARCH_BASE is None
        or settings.LDAP_USER_SEARCH_FILTER is None
    ):
        return None

    server = Server(settings.LDAP_SERVER, get_info=ALL)

    try:
        service_conn = Connection(
            server,
            user=settings.LDAP_BIND_DN,
            password=settings.LDAP_BIND_PASSWORD,
            auto_bind=True,
        )
    except Exception:
        return None

    try:
        search_filter = settings.LDAP_USER_SEARCH_FILTER.format(username=username)
        found = service_conn.search(
            settings.LDAP_USER_SEARCH_BASE,
            search_filter,
            SUBTREE,
            attributes=["displayName", "mail", "sAMAccountName"],
        )
        if not found or not service_conn.entries:
            return None
        entry = service_conn.entries[0]
        user_dn = entry.entry_dn
    finally:
        service_conn.unbind()

    # Проверка пароля — bind под DN самого пользователя.
    try:
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        user_conn.unbind()
    except Exception:
        return None

    return LdapUserInfo(
        username=username,
        full_name=str(entry.displayName) if "displayName" in entry else None,
        email=str(entry.mail) if "mail" in entry else None,
    )
