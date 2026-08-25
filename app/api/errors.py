from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict):
        body = {
            "code": detail.get("code", "HTTP_ERROR"),
            "message": detail.get("message", "请求失败"),
            "details": detail.get("details"),
            "request_id": _request_id(request),
        }
    else:
        body = {
            "code": "HTTP_ERROR",
            "message": str(detail),
            "details": None,
            "request_id": _request_id(request),
        }
    return JSONResponse(status_code=exc.status_code, content=body, headers=exc.headers)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for error in exc.errors():
        details.append(
            {
                "field": ".".join(str(item) for item in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "请求参数校验失败",
            "details": details,
            "request_id": _request_id(request),
        },
    )
