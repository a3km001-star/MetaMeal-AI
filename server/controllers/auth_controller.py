from fastapi import HTTPException, status

from model.auth_model import UserLoginRequest, UserRegisterRequest
from services.auth_service import login_user, register_user


def register_controller(request: UserRegisterRequest):
    try:
        return register_user(request.name, request.email, request.password)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


def login_controller(request: UserLoginRequest):
    try:
        access_token = login_user(request.email, request.password)
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
