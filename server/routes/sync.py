"""Routes for system-level synchronization checks."""

from fastapi import APIRouter

from controllers.sync_controller import check_system_sync_controller
from model.sync_model import SyncCheckRequest, SyncCheckResponse


sync_router = APIRouter(tags=["sync"])


@sync_router.post("/check", response_model=SyncCheckResponse)
def check_system_sync(request: SyncCheckRequest) -> SyncCheckResponse:
    return check_system_sync_controller(request)
