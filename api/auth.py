from datetime import datetime, timedelta
from jose import JWTError, jwt
from werkzeug.security import generate_password_hash, check_password_hash
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .config import settings

bearer = HTTPBearer()

USERS = {
    settings.admin_username: generate_password_hash(settings.admin_password)
}

def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)

def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.token_expire_minutes)
    return jwt.encode(
        {"sub": username, "exp": expire},
        settings.secret_key, algorithm=settings.algorithm
    )

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    exc = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    try:
        payload = jwt.decode(creds.credentials, settings.secret_key, algorithms=[settings.algorithm])
        username: str = payload.get("sub")
        if username not in USERS:
            raise exc
        return username
    except JWTError:
        raise exc
