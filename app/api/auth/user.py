from app.db.models import User


async def insert_user(address: str) -> User:
    user = await User.filter(address=address).first()
    if user:
        return user

    user = await User.create(address=address)

    return user
