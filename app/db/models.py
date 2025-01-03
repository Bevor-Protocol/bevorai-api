from tortoise import fields
from tortoise.models import Model

from app.utils.enums import AuditStatusEnum, AuditTypeEnum, NetworkTypeEnum


class AbstractModel(Model):
    id = fields.UUIDField(primary_key=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.id


class User(AbstractModel):
    address = fields.CharField(
        max_length=42, unique=True
    )  # ETH address is 42 chars with '0x'
    nonce = fields.CharField(max_length=32, null=True)  # For SIWE challenge
    last_login = fields.DatetimeField(null=True)
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "user"

    def __str__(self):
        return f"{self.id} | {self.address}"


class Audit(AbstractModel):
    job_id = fields.CharField(max_length=255, unique=True)
    user_id = fields.CharField(max_length=255, null=True, default=None)
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
        return f"{self.id} | {self.job_id}"


class Contract(AbstractModel):
    contract_address = fields.CharField(max_length=255)
    contract_network = fields.CharEnumField(
        enum_type=NetworkTypeEnum, null=True, default=None
    )
    contract_code = fields.TextField()

    class Meta:
        table = "contract"

    def __str__(self):
        return f"{self.id} | {self.contract_address}"
