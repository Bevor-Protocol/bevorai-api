from fastapi import APIRouter

from .gas import fetch_gas
from .scan import fetch_contract_source_code

router = APIRouter()


@router.get("/scan/{address}")
async def scan_contract(address: str):
    return await fetch_contract_source_code(address)


@router.get("/gas")
async def get_gas():
    return await fetch_gas()
