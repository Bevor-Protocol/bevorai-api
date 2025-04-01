from tortoise.exceptions import DoesNotExist
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.api.audit.service import AuditService
from app.db.models import App, Audit, Auth, Permission, Prompt, User
from app.utils.logger import get_logger
from app.utils.schema.dependencies import AuthState
from app.utils.schema.models import (
    FindingSchema,
    IntermediateResponseSchema,
    PromptSchema,
)
from app.utils.types.enums import AuthScopeEnum, ClientTypeEnum

from .interface import (
    AdminAppPermission,
    AdminPermission,
    AdminUserPermission,
    AuditWithChildren,
    CreatePromptBody,
    UpdatePermissionsBody,
    UpdatePromptBody,
)

logger = get_logger("api")


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
                    id=user.id,
                    created_at=user.created_at,
                    address=user.address,
                    permission=permission,
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
                    created_at=app.created_at,
                    name=app.name,
                    type=app.type,
                    owner_id=app.owner_id,
                    permission=permission,
                )
            )

        return results

    async def get_prompts(self) -> list[PromptSchema]:
        prompts = await Prompt.all()

        return list(map(PromptSchema.from_tortoise, prompts))

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

    async def get_audit_children(self, id: str):

        audit_service = AuditService()

        audit = (
            await Audit.get(id=id)
            .select_related("contract")
            .prefetch_related("intermediate_responses", "findings")
        )

        intermediate_responses = []
        findings = []

        for intermediate in audit.intermediate_responses:
            intermediate_responses.append(
                IntermediateResponseSchema.from_tortoise(intermediate)
            )
        for finding in audit.findings:
            findings.append(FindingSchema.from_tortoise(finding))

        result = None
        if audit.raw_output:
            result = audit_service.sanitize_data(audit=audit, as_markdown=True)

        audit_response = AuditWithChildren(
            id=audit.id,
            created_at=audit.created_at,
            status=audit.status,
            audit_type=audit.audit_type,
            processing_time_seconds=audit.processing_time_seconds,
            result=result,
            intermediate_responses=intermediate_responses,
            findings=findings,
        )

        logger.info(audit_response)

        return audit_response
