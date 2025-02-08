from app.db.models import Auth, User


class AuthService:

    async def request_access(self, address: str):
        user = await User.get(address=address)

        key, hashed = Auth.create_credentials()

        await Auth.create(user=user, hashed_key=hashed)

        return key
