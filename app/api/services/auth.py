from fastapi import HTTPException

from app.api.services.permission import PermissionService
from app.db.models import App, Auth, User
from app.utils.enums import ClientTypeEnum, PermissionEnum


class AuthService:

    async def regenerate_auth(self, address: str, client_type: ClientTypeEnum):
        search_criteria = {}
        if client_type == ClientTypeEnum.APP:
            app = await App.get(owner__address=address)
            search_criteria["app_id"] = app.id
        else:
            user = await User.get(address=address)
            search_criteria["user_id"] = user.id

        auth = await Auth.get(**search_criteria)

        key, hashed = Auth.create_credentials()
        auth.hashed_key = hashed
        await auth.save()

        return key

    async def generate_auth(self, address: str, client_type: ClientTypeEnum):
        permission_service = PermissionService()

        user = await User.get(address=address).prefetch_related("app")
        if client_type == ClientTypeEnum.APP:
            if not user.app:
                raise HTTPException(
                    status_code=401, detail="user must have an app created first"
                )

        identifier = user.id if client_type == ClientTypeEnum.USER else user.app.id
        has_permission = await permission_service.has_permission(
            client_type=client_type,
            identifier=identifier,
            permission=PermissionEnum.CREATE_API_KEY,
        )
        if not has_permission:
            raise HTTPException(status_code=401, detail="incorrect permissions")

        key, hashed = Auth.create_credentials()

        auth = Auth(client_type=client_type, hashed_key=hashed)

        if client_type == ClientTypeEnum.APP:
            auth.app = user.app
        else:
            auth.user = user

        await auth.save()

        return key
