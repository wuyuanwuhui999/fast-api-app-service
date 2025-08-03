from fastapi import Depends
from user.repositories.user import UserRepository
from user.services.auth import AuthService
from common.config.database import get_db

def get_auth_service(db = Depends(get_db)):
    user_repository = UserRepository(db)
    return AuthService(user_repository)