from pydantic import BaseModel


class EvalBody(BaseModel):
    contract: str
    prompt: str
