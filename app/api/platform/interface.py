from openai import BaseModel

"""
Used for HTTP request validation, response Serialization, and arbitrary typing.
"""


class GetCostEstimateResponse(BaseModel):
    credits: int
