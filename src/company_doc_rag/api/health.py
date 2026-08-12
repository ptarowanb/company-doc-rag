from collections.abc import Awaitable, Callable
from typing import cast

from fastapi import APIRouter, HTTPException, Request, status

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """API 프로세스가 요청을 처리할 수 있는지 확인한다."""

    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> dict[str, str]:
    """PostgreSQL과 Redis 연결을 포함한 서비스 준비 상태를 확인한다."""

    check = getattr(request.app.state, "readiness_check", None)
    if check is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="준비 상태 확인기가 설정되지 않았습니다.",
        )
    try:
        await cast(Callable[[], Awaitable[None]], check)()
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="의존 서비스가 준비되지 않았습니다.",
        ) from error
    return {"status": "ready"}
