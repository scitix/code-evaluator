from typing import Any

from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel

from .execution import exec_in_process

app = FastAPI()


class BasicResponse(BaseModel):
    status: bool
    msg: str


@app.get("/health")
async def check_health():
    return BasicResponse(status=True, msg="healthy")


class Sample(BaseModel):
    uuid: str
    source: str
    code: str
    test: str | None = None
    kwargs: dict[str, Any] | None = None


@app.post("/evaluations")
async def evaluate(sample: Sample):
    if sample.source == "human-eval":
        logger.info(f"evaluating sample '{sample.uuid}' from '{sample.source}'...")
        logger.info(f"code to exec:\n{sample.code}")

        ok, msg = exec_in_process(code=sample.code, timeout=3.0)
        return BasicResponse(status=ok, msg=msg)
    else:
        logger.error(f"not supported data source: {sample.source}")

        return BasicResponse(
            status=False, msg=f"not supported data source: {sample.source}"
        )
