from fastapi import APIRouter, HTTPException, Response, Request, Depends, Cookie
from pydantic import BaseModel
from src.services.ldap_client import bind_user
from src.app.auth_service import create_jwt, verify_jwt
from src.config import settings


router = APIRouter()


class LoginSchema(BaseModel):
    email: str
    password: str




@router.post("/login")
async def login(payload: LoginSchema, response: Response):
    ok = bind_user(payload.email, payload.password)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")


    token = create_jwt({"email": payload.email})

    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.JWT_EXP_HOURS * 3600,
        secure=False, # set True in production over HTTPS
    )

    return {"status": "ok"}




@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "logged_out"}




@router.get("/me")
async def me(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    data = verify_jwt(token)
    if not data:
        raise HTTPException(status_code=401, detail="Invalid token")

    return {"email": data.get("email")}