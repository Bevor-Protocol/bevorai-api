from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.db.models import App, Auth, Permission, Prompt, User
from app.utils.schema.dependencies import AuthState
from app.utils.schema.models import PromptSchema
from app.utils.types.enums import AuditTypeEnum, AuthScopeEnum, ClientTypeEnum

from .interface import (
    AdminAppPermission,
    AdminPermission,
    AdminUserPermission,
    CreatePromptBody,
    PromptGroupedResponse,
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
        if type == ClientTypeEnum.APP:
            filter["app_id"] = id
        else:
            filter["user_id"] = id
        permission = await Permission.get(**filter)
        permission.can_create_api_key = body.can_create_api_key
        permission.can_create_app = body.can_create_app
        await permission.save()

    async def search_users(self, identifier: str) -> list[AdminUserPermission]:
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        users = (
            await User.filter(
                Q(id__icontains=identifier) | Q(address__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = []
        for user in users:
            permission = None
            if user.permissions:
                user_permission: Permission = user.permissions
                permission = AdminPermission(
                    can_create_api_key=user_permission.can_create_api_key,
                    can_create_app=user_permission.can_create_app,
                )

            results.append(
                AdminUserPermission(
                    id=user.id, address=user.address, permission=permission
                )
            )

        return results

    async def search_apps(self, identifier: str) -> list[AdminAppPermission]:
        """
        Search for users by either their UUID or address.

        Args:
            identifier: A string that could be either a UUID or an address

        Returns:
            The user object if found, None otherwise
        """
        # Use OR clause to search by ID or address with partial matching

        apps = (
            await App.filter(
                Q(id__icontains=identifier)
                | Q(name__icontains=identifier)
                | Q(owner_id__icontains=identifier)
            )
            .prefetch_related("permissions")
            .limit(10)
        )

        results = []
        for app in apps:
            permission = None
            if app.permissions:
                app_permission: Permission = app.permissions
                permission = AdminPermission(
                    can_create_api_key=app_permission.can_create_api_key,
                    can_create_app=app_permission.can_create_app,
                )

            results.append(
                AdminAppPermission(
                    id=app.id,
                    name=app.name,
                    type=app.type,
                    owner_id=app.owner_id,
                    permission=permission,
                )
            )

        return results

    async def get_prompts_grouped(self) -> PromptGroupedResponse:
        prompts = await Prompt.all()

        prompts_grouped = {k: {} for k in AuditTypeEnum}

        for prompt in prompts:
            audit_type = prompt.audit_type
            tag = prompt.tag
            is_active = prompt.is_active
            if tag not in prompts_grouped[audit_type]:
                prompts_grouped[audit_type][tag] = []

            prompt_instance = PromptSchema.from_tortoise(prompt)

            if is_active:
                prompts_grouped[audit_type][tag].insert(0, prompt_instance)
            else:
                prompts_grouped[audit_type][tag].append(prompt_instance)

        return PromptGroupedResponse(result=prompts_grouped)

    async def update_prompt(self, id: str, body: UpdatePromptBody) -> None:
        if (
            not body.content
            and not body.version
            and not body.tag
            and body.is_active is None
        ):
            return

        prompt = await Prompt.get(id=id)

        prompt_demote = None
        if body.is_active:
            if not prompt.is_active:
                prompt_demote = (
                    await Prompt.filter(
                        id__not=id, tag=prompt.tag, audit_type=prompt.audit_type
                    )
                    .order_by("-created_at")
                    .first()
                )
                if prompt_demote:
                    prompt_demote.is_active = False

        if body.is_active is not None:
            prompt.is_active = body.is_active
        if body.version:
            prompt.version = body.version
        if body.content:
            prompt.content = body.content
        if body.tag:
            prompt.tag = body.tag

        async with in_transaction():
            await prompt.save()
            if prompt_demote:
                await prompt_demote.save()

    async def add_prompt(self, body: CreatePromptBody) -> Prompt:
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
