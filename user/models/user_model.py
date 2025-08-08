from sqlalchemy import Column, String, Integer, DateTime, Boolean
from common.config.common_database import Base
from pydantic import BaseModel

class LoginForm(BaseModel):
    userAccount: str
    password: str