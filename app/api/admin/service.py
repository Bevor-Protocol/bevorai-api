from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.api.audit.service import AuditService
from app.db.models import App, Audit, Auth, Permission, Prompt, User
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum
from app.utils.types.relations import (
    AppPermissionRelation,
    AuditWithChildrenRelation,
    UserPermissionRelation,
)
from app.utils.types.shared import AuthState

from .interface import (
    AuditWithResult,
    CreatePromptBody,
    UpdatePermissionsBody,
    UpdatePromptBody,
)


class AdminService:
    async def is_admin(self, auth_state: AuthState) -> bool:
        try:
            auth = await Auth.get(user_id=auth_state.user_id)
        except DoesNotExist:
            return False
        return auth.scope == AuthScopeEnum.ADMIN

    async def update_permissions(
        self, id: str, client_type: ClientTypeEnum, body: UpdatePermissionsBody
    ) -> None:
        filter = {"client_type": client_type}
        if client_type == ClientTypeEnum.APP:
            filter["app_id"] = id
        else:
            filter["user_id"] = id
        permission = await Permission.get(**filter)
        permission.can_create_api_key = body.can_create_api_key
        permission.can_create_app = body.can_create_app
        await permission.save()

    async def search_users(self, identifier: str) -> list[UserPermissionRelation]:
        users = (
            await User.filter(
                Q(id__icontains=identifier) | Q(address__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = list(map(UserPermissionRelation.model_validate, users))

        return results

    async def search_apps(self, identifier: str) -> list[AppPermissionRelation]:
        apps = (
            await App.filter(
                Q(id__icontains=identifier)
                | Q(name__icontains=identifier)
                | Q(owner_id__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = list(map(AppPermissionRelation.model_validate, apps))

        return results

    async def get_prompts(self) -> list[Prompt]:
        prompts = await Prompt.all()

        return prompts

    async def update_prompt(self, id: str, body: UpdatePromptBody) -> None:
        """Update a prompt and automatically demote a promote, if applicable"""
        prompt = await Prompt.get(id=id)

        prompt_demote = None
        if body.is_active:
            if not prompt.is_active:
                prompt_demote = (
                    await Prompt.filter(
                        id__not=id,
                        tag=prompt.tag,
                        audit_type=body.audit_type or prompt.audit_type,
                    )
                    .order_by("-created_at")
                    .first()
                )
                if prompt_demote:
                    prompt_demote.is_active = False

        async with in_transaction():
            await prompt.update_from_dict(**body.model_dump(exclude_none=True))
            await prompt.save()
            if prompt_demote:
                await prompt_demote.save()

    async def add_prompt(self, body: CreatePromptBody) -> Prompt:
        """Add a prompt and automatically demote a promote, if applicable"""
        prompt = Prompt(
            audit_type=body.audit_type.value,
            tag=body.tag,
            content=body.content,
            version=body.version,
            is_active=body.is_active if body.is_active is not None else False,
        )

        prompt_demote = None
        if body.is_active:
            prompt_demote = (
                await Prompt.filter(
                    id__not=prompt.id, tag=prompt.tag, audit_type=prompt.audit_type
                )
                .order_by("-created_at")
                .first()
            )
            if prompt_demote:
                prompt_demote.is_active = False

        async with in_transaction():
            await prompt.save()
            if prompt_demote:
                await prompt_demote.save()

        return prompt

    async def get_audit_children(self, id: str):
        """Get all corresponding intermediate responses and findings for an audit"""
        audit = (
            await Audit.get(id=id)
            .select_related("contract", "user")
            .prefetch_related("intermediate_responses", "findings", "audit_metadata")
        )

        audit_service = AuditService()
        result = audit_service._parse_branded_markdown(audit=audit)

        return AuditWithResult(
            **AuditWithChildrenRelation.model_validate(audit).model_dump(),
            result=result,
        )
