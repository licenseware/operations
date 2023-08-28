#!/usr/bin/env python


import http
import time

import fastapi
from prometheus_fastapi_instrumentator import Instrumentator

from logger import get_logger
from settings import conf
from tracing import init_tracing
from validator import is_valid_domain, is_valid_email

app = fastapi.FastAPI(title=conf.TRACING_SERVICE_NAME)
init_tracing(app, conf.TRACING_SERVICE_NAME)
instrumentor = Instrumentator().instrument(app)
logger = get_logger(conf.LOG_LEVEL)


@app.on_event("startup")
def startup():
    instrumentor.expose(app)


@app.get("/validate")
async def validate(email: str):
    valid = await is_valid_domain(email) and await is_valid_email(email)

    if valid:
        content = {"valid": True}
        status_code = http.HTTPStatus.OK
    else:
        content = {"valid": False}
        status_code = http.HTTPStatus.BAD_REQUEST

    return fastapi.responses.JSONResponse(content=content, status_code=status_code)


@app.middleware("http")
async def timeit(request: fastapi.Request, call_next):
    start_time = time.time()
    response: fastapi.Response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"Request: {request.method} {request.url.path} | Response: {response.status_code} | Process Time: {process_time:.6f}s"
    )
    return response


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=conf.HOST, port=conf.PORT, reload=conf.DEBUG)
