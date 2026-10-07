import uvicorn
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"status": "ok"}


def main() -> None:
    uvicorn.run("ai_microservice.main:app", host="127.0.0.1", port=8000, reload=True)
