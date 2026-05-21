"""CLI создания первого администратора. Запуск: python -m app.scripts.create_admin"""

import asyncio
import getpass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.models.users import User
from app.db.session import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as db:
        existing = await db.scalar(select(User).where(User.role == "admin"))
        if existing is not None:
            print(f"Администратор уже существует: {existing.username}")
            return

        username = input("Username: ").strip()
        full_name = input("Full name: ").strip() or None
        email = input("Email (optional): ").strip() or None
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm: ")

        if not username or not password:
            print("Username и пароль обязательны")
            return
        if password != confirm:
            print("Пароли не совпадают")
            return

        user = User(
            username=username,
            full_name=full_name,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Создан администратор id={user.id}")


if __name__ == "__main__":
    asyncio.run(main())
