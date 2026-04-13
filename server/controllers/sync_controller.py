"""Controller for cross-module synchronization checks."""

from model.sync_model import SyncCheckRequest, SyncCheckResponse
from services.sync_service import evaluate_sync


def check_system_sync_controller(request: SyncCheckRequest) -> SyncCheckResponse:
    return evaluate_sync(request)
