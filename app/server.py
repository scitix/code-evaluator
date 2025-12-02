import atexit
import os
import sys
from typing import Any

from fastapi import FastAPI
from loguru import logger
from pydantic import BaseModel

from .exec_js import execute_code as exec_js
from .exec_py_code import execute_code as exec_py_code
from .exec_py_test import execute_test as exec_py_test
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


class LiveCodeBenchTest(BaseModel):
    inputs: list[str]
    outputs: list[str]
    fn_name: str | None = None


class Sample(BaseModel):
    uuid: str
    source: str
    code: str
    test: LiveCodeBenchTest | None = None
    lang: str = "python"
    timeout: float | None = None
    memory_limit: int = 1024  # MB
    kwargs: dict[str, Any] | None = None


@app.post("/evaluations")
async def evaluate(sample: Sample):
    if sample.source == "human-eval":
        # 'human-eval' directly use the code
        logger.debug(f"code to exec:\n{sample.code}")

        CODE_EXECUTOR_MAP = {
            "javascript": (exec_js, 3.0),
            "python": (exec_py_code, 3.0),
            "typescript": (exec_ts, 5.0),
        }
        if sample.lang in CODE_EXECUTOR_MAP:
            fn, default_timeout = CODE_EXECUTOR_MAP[sample.lang]
            timeout = sample.timeout if sample.timeout is not None else default_timeout
            ok, msg = await fn(
                code=sample.code, timeout=timeout, memory_limit=sample.memory_limit
            )
        else:
            ok, msg = False, f"not supported language: {sample.lang}"

        logger.info(
            f"evaluate sample '{sample.uuid}' from '{sample.source}', "
            f"language: {sample.lang}, timeout: {timeout}, memory_limit: {sample.memory_limit}, "
            f"kwargs: {sample.kwargs}, status: {ok}, msg: {msg}"
        )
        return BasicResponse(status=ok, msg=msg)
    elif sample.source == "livecodebench":
        # 'livecodebench' use tests to eval the code
        logger.debug(f"code to exec:\n{sample.code}")

        if sample.lang != "python":
            return BasicResponse(
                status=False, msg=f"not supported language: {sample.lang}"
            )

        if sample.test is None:
            timeout = sample.timeout if sample.timeout is not None else 3.0
            ok, msg = await exec_py_code(
                code=sample.code, timeout=timeout, memory_limit=sample.memory_limit
            )
        else:
            default_timeout = 6.0 + len(sample.test.inputs) * 2.0
            timeout = sample.timeout if sample.timeout is not None else default_timeout
            ok, msg = await exec_py_test(
                code=sample.code,
                inputs=sample.test.inputs,
                expect_outputs=sample.test.outputs,
                fn_name=sample.test.fn_name,
                timeout=timeout,
                memory_limit=sample.memory_limit,
            )

        logger.info(
            f"evaluate sample '{sample.uuid}' from '{sample.source}', "
            f"language: {sample.lang}, timeout: {timeout}, memory_limit: {sample.memory_limit}, "
            f"kwargs: {sample.kwargs}, status: {ok}, msg: {msg}"
        )
        return BasicResponse(status=ok, msg=msg)
    else:
        logger.error(f"not supported data source: {sample.source}")
        return BasicResponse(
            status=False, msg=f"not supported data source: {sample.source}"
        )
