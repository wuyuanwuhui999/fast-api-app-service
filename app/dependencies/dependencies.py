from fastapi import Depends
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.database import get_db

def get_auth_service(db = Depends(get_db)):
    user_repository = UserRepository(db)
    return AuthService(user_repository)