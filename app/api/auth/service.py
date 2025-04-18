from fastapi import HTTPException, status

from app.api.permission.service import PermissionService
from app.db.models import App, Auth, User
from app.utils.types.enums import ClientTypeEnum, PermissionEnum
from app.utils.types.shared import AuthState


class AuthService:
    async def generate(self, auth_obj: AuthState, client_type: ClientTypeEnum):
        # only callable via FIRST_PARTY app, we know to reference the user obj.
        search_criteria = {}
        identifier = None
        if client_type == ClientTypeEnum.APP:
            app = await App.get(owner_id=auth_obj.user_id)
            search_criteria["app_id"] = app.id
            identifier = app.id
        else:
            user = await User.get(id=auth_obj.user_id)
            search_criteria["user_id"] = user.id
            identifier = user.id

        auth = await Auth.filter(**search_criteria).first()
        api_key, hash_key = Auth.create_credentials()
        if auth:
            # regenerate
            auth.hashed_key = hash_key
            await auth.save()
            return api_key

        # evaluate permissions, then create
        permission_service = PermissionService()

        has_permission = await permission_service.has_permission(
            client_type=client_type,
            identifier=identifier,
            permission=PermissionEnum.CREATE_API_KEY,
        )
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="incorrect permissions"
            )

        await Auth.create(
            **search_criteria, client_type=client_type, hashed_key=hash_key
        )

        return api_key

    async def revoke_access(self):
        pass
