import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_microservice.config import get_settings
from ai_microservice.modules.novelty.router import router as novelty_router

app = FastAPI(title="STS 2026 — AI microservice")
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(novelty_router)


@app.get("/")
def read_root():
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("ai_microservice.main:app", host="127.0.0.1", port=8000, reload=True)
