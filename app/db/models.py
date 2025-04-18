import hashlib
import secrets

from tortoise import fields
from tortoise.models import Model

from app.utils.types.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    AuthScopeEnum,
    ChatRoleEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    CreditTierEnum,
    FindingLevelEnum,
    NetworkEnum,
    TransactionTypeEnum,
)


class AbstractModel(Model):
    id = fields.UUIDField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return str(self.id)


class User(AbstractModel):
    address = fields.CharField(max_length=255)
    total_credits = fields.FloatField(default=0)
    used_credits = fields.FloatField(default=0)

    # users can own 0 to many apps
    apps: fields.ReverseRelation["App"]
    audits: fields.ReverseRelation["Audit"]
    auth: fields.ReverseRelation["Auth"]
    permissions: fields.ReverseRelation["Permission"]

    class Meta:
        table = "user"
        indexes = ("address",)

    def __str__(self):
        return f"{str(self.id)} | {self.address}"


class App(AbstractModel):
    # Every app will have an owner, unless it's a first party app.
    owner: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="apps"
    )
    name = fields.CharField(max_length=255)
    type = fields.CharEnumField(enum_type=AppTypeEnum, default=AppTypeEnum.THIRD_PARTY)

    auth: fields.ReverseRelation["Auth"]
    audits: fields.ReverseRelation["Audit"]
    permissions: fields.ReverseRelation["Permission"]

    class Meta:
        table = "app"
        indexes = ("type",)

    def __str__(self):
        return f"{str(self.id)} | {self.name} | {self.type}"


class Auth(AbstractModel):
    app: fields.OneToOneNullableRelation[App] = fields.OneToOneField(
        "models.App", on_delete=fields.CASCADE, null=True, related_name="auth"
    )
    user: fields.OneToOneNullableRelation[User] = fields.OneToOneField(
        "models.User", on_delete=fields.CASCADE, null=True, related_name="auth"
    )
    client_type = fields.CharEnumField(
        enum_type=ClientTypeEnum, default=ClientTypeEnum.USER
    )
    hashed_key = fields.CharField(max_length=255)
    revoked_at = fields.DatetimeField(null=True, default=None)
    scope = fields.CharEnumField(enum_type=AuthScopeEnum, default=AuthScopeEnum.WRITE)
    consumes_credits = fields.BooleanField(default=True)

    class Meta:
        table = "auth"
        indexes = ("hashed_key",)

    def __str__(self):
        return str(self.id)

    @staticmethod
    def create_credentials():
        api_key = secrets.token_urlsafe(32)
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, hashed_key

    @staticmethod
    def hash_key(api_key: str):
        return hashlib.sha256(api_key.encode()).hexdigest()


class Credit(AbstractModel):
    tier = fields.CharEnumField(enum_type=CreditTierEnum)
    value = fields.FloatField(default=1.0)

    class Meta:
        table = "credit"

    def __str__(self):
        return f"{self.tier} | {self.value} credits per request"


class Transaction(AbstractModel):
    app: fields.ForeignKeyNullableRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True, related_name="transactions"
    )
    user: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="transactions"
    )
    type = fields.CharEnumField(enum_type=TransactionTypeEnum)
    amount = fields.FloatField()

    class Meta:
        table = "transaction"

    def __str__(self):
        return f"{str(self.id)} | {self.type} | {self.amount}"


class Contract(AbstractModel):
    method = fields.CharEnumField(enum_type=ContractMethodEnum)
    is_available = fields.BooleanField(
        default=True, description="whether source code is available"
    )
    address = fields.CharField(max_length=255, null=True, default=None)
    network = fields.CharEnumField(enum_type=NetworkEnum, null=True, default=None)
    contract_name = fields.TextField(null=True, default=None)
    is_proxy = fields.BooleanField(default=False)
    code = fields.TextField(null=True, default=None)
    hashed_code = fields.CharField(max_length=255, null=True, default=None)

    class Meta:
        table = "contract"

    def __str__(self):
        return f"{str(self.id)} | {self.address}"

    @classmethod
    async def create(self, *args, **kwargs):
        code = kwargs.get("code")
        if code:
            kwargs["hashed_code"] = hashlib.sha256(code.encode()).hexdigest()
        return await super().create(*args, **kwargs)

    async def save(self, *args, **kwargs):
        code = kwargs.get("code")
        if code:
            kwargs["hashed_code"] = hashlib.sha256(code.encode()).hexdigest()
        await super().save(*args, **kwargs)


class Audit(AbstractModel):
    app: fields.ForeignKeyNullableRelation[App] = fields.ForeignKeyField(
        "models.App", on_delete=fields.SET_NULL, null=True, related_name="audits"
    )
    user: fields.ForeignKeyNullableRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.SET_NULL, null=True, related_name="audits"
    )
    contract: fields.ForeignKeyRelation[Contract] = fields.ForeignKeyField(
        "models.Contract", on_delete=fields.CASCADE, related_name="audits"
    )
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    status = fields.CharEnumField(
        enum_type=AuditStatusEnum, null=True, default=AuditStatusEnum.WAITING
    )
    raw_output = fields.TextField(null=True, default=None)
    introduction = fields.TextField(null=True, default=None)
    scope = fields.TextField(null=True, default=None)
    conclusion = fields.TextField(null=True, default=None)
    input_tokens = fields.IntField(null=True, default=0)
    output_tokens = fields.IntField(null=True, default=0)
    processing_time_seconds = fields.IntField(null=True, default=None)

    intermediate_responses: fields.ReverseRelation["IntermediateResponse"]
    findings: fields.ReverseRelation["Finding"]

    class Meta:
        table = "audit"
        indexes = (
            ("user_id",),
            ("user_id", "audit_type", "contract_id"),
            ("user_id", "audit_type"),
            ("audit_type", "contract_id"),
        )

    def __str__(self):
        return f"{str(self.id)}"


class IntermediateResponse(AbstractModel):
    audit: fields.ForeignKeyRelation[Audit] = fields.ForeignKeyField(
        "models.Audit", on_delete=fields.CASCADE, related_name="intermediate_responses"
    )
    step = fields.CharField(max_length=30)
    status = fields.CharEnumField(
        enum_type=AuditStatusEnum, null=True, default=AuditStatusEnum.WAITING
    )
    processing_time_seconds = fields.IntField(null=True, default=None)
    result = fields.TextField(null=True, default=None)
    prompt: fields.ForeignKeyNullableRelation["Prompt"] = fields.ForeignKeyField(
        "models.Prompt",
        on_delete=fields.SET_NULL,
        null=True,
        related_name="intermediate_responses",
    )

    class Meta:
        table = "intermediate_response"

    def __str__(self):
        return f"{str(self.id)} | {self.audit_id}"


class Finding(AbstractModel):
    audit: fields.ForeignKeyRelation[Audit] = fields.ForeignKeyField(
        "models.Audit", on_delete=fields.CASCADE, related_name="findings"
    )
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    level = fields.CharEnumField(enum_type=FindingLevelEnum)
    name = fields.TextField(null=True, default=None)
    explanation = fields.TextField(null=True, default=None)
    recommendation = fields.TextField(null=True, default=None)
    reference = fields.TextField(null=True, default=None)
    is_attested = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)
    feedback = fields.TextField(null=True, default=None)
    attested_at = fields.DatetimeField(null=True, default=None)

    class Meta:
        table = "finding"
        indexes = (("audit_id",), ("audit_id", "level"))

    def __str__(self):
        return f"{str(self.id)} | {self.audit_id}"


class Prompt(AbstractModel):
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    tag = fields.CharField(max_length=50)  # "step" or component prompt of audit
    version = fields.CharField(max_length=20)
    content = fields.TextField()
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "prompt"
        indexes = (
            ("audit_type",),
            ("audit_type", "tag"),
        )

    def __str__(self):
        return f"{self.audit_type} | {self.tag} | v{self.version}"


class Permission(AbstractModel):
    client_type = fields.CharEnumField(enum_type=ClientTypeEnum)
    user: fields.OneToOneNullableRelation[User] = fields.OneToOneField(
        "models.User", on_delete=fields.CASCADE, null=True, related_name="permissions"
    )
    app: fields.OneToOneNullableRelation[App] = fields.OneToOneField(
        "models.App", on_delete=fields.CASCADE, null=True, related_name="permissions"
    )
    can_create_app = fields.BooleanField(default=False)
    can_create_api_key = fields.BooleanField(default=False)

    class Meta:
        table = "permission"
        indexes = (("user_id",), ("app_id",))

    def __str__(self):
        return f"{str(self.id)} | {str(self.client_type)}"


class Chat(AbstractModel):
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", on_delete=fields.CASCADE, related_name="chats"
    )
    audit: fields.ForeignKeyRelation[Audit] = fields.ForeignKeyField(
        "models.Audit", on_delete=fields.CASCADE, related_name="chats"
    )
    is_visible = fields.BooleanField(default=True)
    total_messages = fields.IntField(default=0)

    messages: fields.ReverseRelation["ChatMessage"]

    class Meta:
        table = "chat"
        indexes = (("user_id",), ("audit_id",), ("is_visible", "user_id"))

    def __str__(self):
        return str(self.id)


class ChatMessage(AbstractModel):
    chat: fields.ForeignKeyRelation[Chat] = fields.ForeignKeyField(
        "models.Chat", on_delete=fields.CASCADE, related_name="messages"
    )
    chat_role = fields.CharEnumField(enum_type=ChatRoleEnum)
    message = fields.TextField()
    n_tokens = fields.IntField()  # n_tokens of the response output, stored in `message`
    model_name = fields.TextField()  # model used to generate embeddings
    embedding = fields.JSONField(null=True)  # we'll store a vector here.
