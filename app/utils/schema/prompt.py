from app.utils.schema.shared import CreatedAtResponse, IdResponse


class PromptPydantic(IdResponse, CreatedAtResponse):
    audit_type: str
    tag: str
    version: str
    content: str
    is_active: bool
