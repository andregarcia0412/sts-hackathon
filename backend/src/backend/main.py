from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from backend.database import close_db, init_db, ping_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health/db")
async def db_health():
    return {"mongo": "ok" if await ping_db() else "unreachable"}


def main() -> None:
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
