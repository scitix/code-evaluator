import atexit
import os
import sys
from typing import Any

from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel

from .exec_js import execute_code as exec_js
from .exec_py import execute_code as exec_py
from .exec_ts import execute_code as exec_ts

# logger
logger.configure(
    handlers=[
        {
            "sink": sys.stdout,
            "level": os.getenv("LOG_LEVEL", "INFO"),
            "enqueue": True,
        }
    ],
)


# collect non-server loggers
@atexit.register
def exit_handler():
    logger.remove()


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
    lang: str = "python"
    kwargs: dict[str, Any] | None = None


@app.post("/evaluations")
async def evaluate(sample: Sample):
    if sample.source == "human-eval":
        logger.info(
            f"evaluating sample '{sample.uuid}' from '{sample.source}', language: {sample.lang}"
        )
        logger.debug(f"code to exec:\n{sample.code}")

        CODE_EXECUTOR_MAP = {
            "javascript": (exec_js, 3.0),
            "python": (exec_py, 3.0),
            "typescript": (exec_ts, 5.0),
        }
        if sample.lang in CODE_EXECUTOR_MAP:
            fn, timeout = CODE_EXECUTOR_MAP[sample.lang]
            ok, msg = await fn(code=sample.code, timeout=timeout)
        else:
            ok, msg = False, f"not supported language: {sample.lang}"
        logger.debug(f"status: {ok}, msg: {msg}")

        return BasicResponse(status=ok, msg=msg)
    else:
        logger.error(f"not supported data source: {sample.source}")

        return BasicResponse(
            status=False, msg=f"not supported data source: {sample.source}"
        )
