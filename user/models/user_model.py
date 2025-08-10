from pydantic import BaseModel

class LoginForm(BaseModel):
    userAccount: str
    password: str