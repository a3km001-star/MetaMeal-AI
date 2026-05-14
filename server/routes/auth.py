from fastapi import APIRouter, Depends, status

from controllers.auth_controller import login_controller, register_controller
from model.auth_model import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from services.auth_service import get_current_user


auth_router = APIRouter(prefix="/auth", tags=["auth"])


@auth_router.post("/register", response_model=UserResponse)
def register(request: UserRegisterRequest):
    return register_controller(request)


@auth_router.post("/login", response_model=TokenResponse)
def login(request: UserLoginRequest):
    return login_controller(request)


@auth_router.get("/me", response_model=UserResponse)
def read_current_user(current_user: UserResponse = Depends(get_current_user)):
    return current_user

# Basic test endpoint
@auth_router.get("/test", status_code=status.HTTP_200_OK)
def test_endpoint():
    return {"message": "OK"}