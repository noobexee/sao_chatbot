from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.app.auth.authen import auth_manager as auth

router = APIRouter()

#  LOGIN 
@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    return auth.login(form_data.username, form_data.password)

# ADMIN ONLY

# view all users
@router.get("/users")
def get_all_users(
    current_user=Depends(auth.require_roles(["admin"]))
):
    return auth.get_all_users(current_user)

# create user
@router.post("/users")
def create_user(
    username: str,
    password: str,
    role: str,
    current_user=Depends(auth.require_roles(["admin"]))
):
    return auth.create_user(current_user, username, password, role)

# update user
@router.put("/users/{user_id}")
def update_user(
    user_id: str,
    username: str,
    password: str,
    role: str,
    current_user=Depends(auth.require_roles(["admin"]))
):
    return auth.update_user(current_user, user_id, username, password, role)

# delete user
@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user=Depends(auth.require_roles(["admin"]))
):
    return auth.delete_user(current_user, user_id)