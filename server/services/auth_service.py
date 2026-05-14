import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config import ACCESS_TOKEN_EXPIRE_MINUTES, JWT_ALGORITHM, JWT_SECRET, PASSWORD_HASH_ITERATIONS
from db.mongo import users_collection

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign_message(message: bytes) -> str:
    signature = hmac.new(JWT_SECRET.encode("utf-8"), message, hashlib.sha256).digest()
    return _base64url_encode(signature)


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"{salt.hex()}:{derived_key.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        expected_key = bytes.fromhex(key_hex)
    except ValueError:
        return False

    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return hmac.compare_digest(derived_key, expected_key)


def _create_jwt(payload: Dict[str, Any]) -> str:
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    encoded_header = _base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    message = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = _sign_message(message)
    return f"{encoded_header}.{encoded_payload}.{signature}"


def _decode_jwt(token: str) -> Dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    message = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    expected_signature = _sign_message(message)
    if not hmac.compare_digest(encoded_signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    try:
        payload_json = _base64url_decode(encoded_payload)
        payload = json.loads(payload_json)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication payload")

    exp = payload.get("exp")
    if exp is None or not isinstance(exp, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication payload")
    if datetime.utcnow().timestamp() > exp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token has expired")

    return payload


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.utcnow()
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return _create_jwt(payload)


def _sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    if not user:
        return None
    return {
        "id": str(user.get("_id")) if user.get("_id") is not None else None,
        "name": user.get("name"),
        "email": user.get("email"),
        "created_at": user.get("created_at"),
        "user_details": user.get("user_details"),
        "first_meal_generation": user.get("first_meal_generation"),
        "last_meal_generation_date": user.get("last_meal_generation_date"),
        "meal_generation_streak": int(user.get("meal_generation_streak", 0) or 0),
    }


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    return users_collection.find_one({"email": email.lower()})


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return None
    return users_collection.find_one({"_id": object_id})


def _get_user_from_token(token: str) -> Dict[str, Any]:
    payload = _decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return _sanitize_user(user)


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    return _get_user_from_token(token)


def get_current_user_optional(token: str = Depends(optional_oauth2_scheme)) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    return _get_user_from_token(token)


def update_user_details(user_id: str, user_details: Dict[str, Any]) -> None:
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return

    try:
        users_collection.update_one(
            {"_id": object_id},
            {"$set": {"user_details": user_details}},
            upsert=False,
        )
    except Exception as exc:
        logger.warning("Failed to update user details: %s", exc)


def _parse_iso_date(date_value: Any) -> Optional[date]:
    if not isinstance(date_value, str):
        return None
    try:
        return date.fromisoformat(date_value)
    except ValueError:
        return None


def _calculate_meal_generation_streak(last_date_str: Optional[str], current_streak: int) -> int:
    today = date.today()
    last_date = _parse_iso_date(last_date_str)
    if last_date == today:
        return current_streak if current_streak >= 0 else 1
    if last_date == today - timedelta(days=1):
        return max(current_streak, 1) + 1
    return 1


def record_meal_generation_event(user_id: str, meal_request_data: Dict[str, Any]) -> None:
    try:
        object_id = ObjectId(user_id)
    except Exception:
        return

    try:
        user = users_collection.find_one({"_id": object_id})
        if not user:
            return

        streak = int(user.get("meal_generation_streak", 0) or 0)
        last_generation_date = user.get("last_meal_generation_date")
        new_streak = _calculate_meal_generation_streak(last_generation_date, streak)

        update_payload: Dict[str, Any] = {
            "last_meal_generation_date": date.today().isoformat(),
            "meal_generation_streak": new_streak,
        }

        if "first_meal_generation" not in user:
            first_generation_payload = {
                "age": meal_request_data.get("age"),
                "sex": meal_request_data.get("sex"),
                "height": meal_request_data.get("height"),
                "weight": meal_request_data.get("weight"),
                "diet_type": meal_request_data.get("diet_type"),
                "activity_level": meal_request_data.get("activity_level"),
                "goal": meal_request_data.get("goal"),
                "allergies": meal_request_data.get("allergies", []),
                "generated_at": datetime.utcnow().isoformat(),
            }
            update_payload["first_meal_generation"] = first_generation_payload

        users_collection.update_one(
            {"_id": object_id},
            {"$set": update_payload},
            upsert=False,
        )
    except Exception as exc:
        logger.warning("Failed to record meal generation event: %s", exc)


def register_user(name: str, email: str, password: str) -> Dict[str, Any]:
    if get_user_by_email(email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with that email already exists")

    user_record = {
        "name": name,
        "email": email.lower(),
        "password_hash": _hash_password(password),
        "created_at": datetime.utcnow(),
    }
    result = users_collection.insert_one(user_record)
    user_record["_id"] = result.inserted_id
    return _sanitize_user(user_record)


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    user = get_user_by_email(email)
    if not user or not _verify_password(password, user.get("password_hash", "")):
        return None
    return _sanitize_user(user)


def login_user(email: str, password: str) -> str:
    user = get_user_by_email(email)
    if not user or not _verify_password(password, user.get("password_hash", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return create_access_token(subject=str(user["_id"]))


def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, Any]:
    payload = _decode_jwt(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")

    user = get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return _sanitize_user(user)
