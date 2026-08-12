from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """API 프로세스가 요청을 처리할 수 있는지 확인한다."""

    return {"status": "ok"}

