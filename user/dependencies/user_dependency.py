from fastapi import Depends
from user.repositories.user_repository import UserRepository
from user.services.auth_service import AuthService
from common.config.common_database import get_db

def get_auth_service(db = Depends(get_db)):
    user_repository = UserRepository(db)
    return AuthService(user_repository)