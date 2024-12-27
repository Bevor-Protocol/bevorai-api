from dotenv import load_dotenv
from fastapi import FastAPI

from .ai.routes import router as ai_router
from .blockchain.routes import router as blockchain_router

load_dotenv()
app = FastAPI()


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/health")
async def health_check():
    return True


app.include_router(prefix="/blockchain", router=blockchain_router)
app.include_router(prefix="/ai", router=ai_router)
