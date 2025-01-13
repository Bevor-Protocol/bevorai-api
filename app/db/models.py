import hashlib
import secrets

from tortoise import fields
from tortoise.models import Model

from app.utils.enums import (
    AppTypeEnum,
    AuditStatusEnum,
    AuditTypeEnum,
    ClientTypeEnum,
    ContractMethodEnum,
    CreditTierEnum,
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
    address = fields.CharField(max_length=255, unique=True)
    total_credits = fields.IntField(default=0)
    remaining_credits = fields.IntField(default=0)

    class Meta:
        table = "user"

    def __str__(self):
        return f"{str(self.id)} | {self.address}"


class App(AbstractModel):
    # Every app will have an owner, unless it's a first party app.
    name = fields.CharField(max_length=255)
    owner = fields.ForeignKeyField("models.User", null=True)
    type = fields.CharEnumField(enum_type=AppTypeEnum, default=AppTypeEnum.THIRD_PARTY)

    class Meta:
        table = "app"

    def __str__(self):
        return f"{str(self.id)} | {self.name} | {self.type}"


class Auth(AbstractModel):
    client_type = fields.CharEnumField(
        enum_type=ClientTypeEnum, default=ClientTypeEnum.USER
    )
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, null=True)
    app = fields.ForeignKeyField("models.App", on_delete=fields.CASCADE, null=True)

    hashed_key = fields.CharField(max_length=255)
    is_revoked = fields.BooleanField(default=False)

    class Meta:
        table = "auth"

    def __str__(self):
        return str(self.id)

    @staticmethod
    def create_credentials():
        api_key = secrets.token_urlsafe(32)
        hashed_key = hashlib.sha256(api_key.encode()).hexdigest()
        return api_key, hashed_key


class Credit(AbstractModel):
    tier = fields.CharEnumField(enum_type=CreditTierEnum)
    value = fields.FloatField(default=1.0)

    class Meta:
        table = "credit"

    def __str__(self):
        return f"{self.tier} | {self.value} credits per request"


class Transaction(AbstractModel):
    app = fields.ForeignKeyField("models.App", on_delete=fields.CASCADE, null=True)
    user = fields.ForeignKeyField("models.User", on_delete=fields.CASCADE, null=True)
    type = fields.CharEnumField(enum_type=TransactionTypeEnum)
    amount = fields.FloatField()

    class Meta:
        table = "transaction"

    def __str__(self):
        return f"{str(self.id)} | {self.type} | {self.amount}"


class Audit(AbstractModel):
    job_id = fields.CharField(max_length=255, unique=True)
    app = fields.ForeignKeyField("models.App", null=True)
    user = fields.ForeignKeyField("models.User", null=True)
    contract = fields.ForeignKeyField("models.Contract")
    prompt_version = fields.IntField()
    model = fields.CharField(max_length=255)
    audit_type = fields.CharEnumField(enum_type=AuditTypeEnum)
    processing_time_seconds = fields.IntField(null=True, default=None)
    results_status = fields.CharEnumField(
        enum_type=AuditStatusEnum, null=True, default=AuditStatusEnum.WAITING
    )
    results_raw_output = fields.TextField(null=True, default=None)

    class Meta:
        table = "audit"

    def __str__(self):
        return f"{str(self.id)} | {self.job_id}"


class Contract(AbstractModel):
    method = fields.CharEnumField(enum_type=ContractMethodEnum)
    is_available = fields.BooleanField(
        default=True, description="if via cron, whether source code is available"
    )
    n_retries = fields.IntField(
        default=0, description="current # of retries to get source code"
    )
    next_attempt = fields.DatetimeField(
        auto_now=True,
        description="if source code unavailable, next timestamp to allow scan",
    )
    address = fields.CharField(max_length=255, null=True, default=None)
    network = fields.CharEnumField(enum_type=NetworkEnum, null=True, default=None)
    raw_code = fields.TextField(null=True, default=None)
    hash_code = fields.CharField(max_length=255, null=True, default=None)

    class Meta:
        table = "contract"

    def __str__(self):
        return f"{str(self.id)} | {self.job_id}"
