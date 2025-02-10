from app.db.models import Permission
from app.utils.enums import ClientTypeEnum, PermissionEnum


class PermissionService:

    async def has_permission(
        self,
        client_type: ClientTypeEnum,
        identifier: str,
        permission: PermissionEnum | list[PermissionEnum],
    ):
        obj = {}
        if isinstance(permission, list):
            for p in permission:
                obj[p] = True
        else:
            obj[permission] = True

        if client_type == ClientTypeEnum.APP:
            obj["app_id"] = identifier
        else:
            obj["user_id"] = identifier

        exists = await Permission.exists(**obj)
        return exists

    async def update_permission(
        self,
        client_type: ClientTypeEnum,
        identifier: str,
        permission: PermissionEnum,
        allowed: bool,
    ):
        obj = {permission: True}
        if client_type == ClientTypeEnum.APP:
            obj["app_id"] = identifier
        else:
            obj["user_id"] = identifier

        obs = await Permission.get(**obj)
        setattr(obs, permission, allowed)
        await obs.save()

    async def create_permission(self, client_type: ClientTypeEnum, identifier: str):
        obj = {"client_type": client_type}
        if client_type == ClientTypeEnum.APP:
            obj["app_id"] = identifier
        else:
            obj["user_id"] = identifier

        await Permission.create(**obj)
