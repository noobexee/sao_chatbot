from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta

from src.db.repositories.auth_repository import AuthRepository


# ===== CONFIG =====
SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 600

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class AuthManager:

    def __init__(self):
        self.repo = AuthRepository()

    # CREATE TOKEN 
    def create_access_token(self, data: dict, expires_delta: timedelta = None):
        to_encode = data.copy()

        expire = datetime.utcnow() + (
            expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        to_encode.update({"exp": expire})

        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    # LOGIN
    def login(self, username: str, password: str):
        user = self.repo.authenticate_user(username, password)

        if not user:
            raise HTTPException(401, "Invalid username or password")

        token = self.create_access_token(
            data={
                "sub": user["username"],
                "role": user["role"]
            }
        )

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"]
            }
        }

    # GET CURRENT USER
    def get_current_user(self, token: str = Depends(oauth2_scheme)):
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

            username: str = payload.get("sub")
            role: str = payload.get("role")

            if username is None or role is None:
                raise credentials_exception

        except JWTError:
            raise credentials_exception

        user = self.repo.get_user_by_username(username)

        if not user:
            raise credentials_exception

        if not user["is_active"]:
            raise HTTPException(403, "User is inactive")

        return user

    # ROLE CHECK
    def require_roles(self, allowed_roles: list):
        def role_checker(user=Depends(self.get_current_user)):
            if user["role"] not in allowed_roles:
                raise HTTPException(403, "Permission denied")
            return user

        return role_checker
    
    # ADMIN ACTIONS
    def get_all_users(self, current_user):
        if current_user["role"] != "admin":
            raise HTTPException(403, "Only admin can view users")

        return self.repo.get_all_users()
    def create_user(self, current_user, username, password, role):
        if current_user["role"] != "admin":
            raise HTTPException(403, "Only admin can create users")

        return self.repo.create_user(username, password, role)

    def update_user(self, current_user, user_id, username, password, role):
        if current_user["role"] != "admin":
            raise HTTPException(403, "Only admin can update users")

        return self.repo.update_user(user_id, username, password, role)

    def delete_user(self, current_user, user_id):
        if current_user["role"] != "admin":
            raise HTTPException(403, "Only admin can delete users")

        return self.repo.delete_user(user_id)



auth_manager = AuthManager()