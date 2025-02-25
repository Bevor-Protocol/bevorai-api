from app.db.models import Permission
from app.utils.enums import ClientTypeEnum, PermissionEnum


class PermissionService:

    async def has_permission(
        self,
        client_type: ClientTypeEnum,
        identifier: str,
        permission: PermissionEnum | list[PermissionEnum],
    ) -> bool:
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

    async def update(
        self,
        client_type: ClientTypeEnum,
        identifier: str,
        permission: PermissionEnum,
        allowed: bool,
    ) -> None:
        obj = {permission: True}
        if client_type == ClientTypeEnum.APP:
            obj["app_id"] = identifier
        else:
            obj["user_id"] = identifier

        obs = await Permission.get(**obj)
        setattr(obs, permission, allowed)
        await obs.save()

    async def create(
        self,
        client_type: ClientTypeEnum,
        identifier: str,
        permissions: dict[str, bool] = {},
    ) -> None:
        obj = {"client_type": client_type, **permissions}
        if client_type == ClientTypeEnum.APP:
            obj["app_id"] = identifier
        else:
            obj["user_id"] = identifier

        await Permission.create(**obj)
