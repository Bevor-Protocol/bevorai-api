from fastapi import APIRouter

from app.types import EvalBody

from .eval import process_evaluation

router = APIRouter()


@router.post("/eval")
async def evaluate_contract(data: EvalBody):
    return await process_evaluation(data)
