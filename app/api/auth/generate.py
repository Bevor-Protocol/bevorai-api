from app.db.models import Auth, User


async def request_access(address: str):
    user = await User.get(address=address)

    key, hashed = Auth.create_credentials()

    await Auth.create(user=user, hashed_key=hashed)

    return key
