from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from app.db.models import App, Permission
from app.schema.dependencies import AuthDict
from app.schema.request import AppUpsertBody
from app.utils.enums import AppTypeEnum, ClientTypeEnum


class AppService:
    async def create_app(self, auth: AuthDict, body: AppUpsertBody) -> App:

        app = await App.filter(owner_id=auth["user"].id).first()
        if app:
            return True

        async with in_transaction():
            app = await App.create(
                owner_id=auth["user"].id, name=body.name, type=AppTypeEnum.THIRD_PARTY
            )
            await Permission.create(
                client_type=ClientTypeEnum.APP, app_id=app.id, can_create_api_key=True
            )

        return True

    async def update_app(self, auth: AuthDict, body: AppUpsertBody) -> App:

        app = await App.filter(owner_id=auth["user"].id).first()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="this user does not an app yet",
            )
        app.name = body.name
        await app.save()

        return True
