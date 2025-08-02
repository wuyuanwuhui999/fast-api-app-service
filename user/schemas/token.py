from pydantic import BaseModel
from typing import Optional

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    id: Optional[str] = None
    username: Optional[str] = None
    userAccount: Optional[str] = None
    avater: Optional[str] = None
    birthday: Optional[str] = None
    createDate: Optional[str] = None
    disabled: Optional[int] = None
    email: Optional[str] = None
    permission: Optional[int] = None
    role: Optional[str] = None
    sex: Optional[int] = None
    sign: Optional[str] = None
    telephone: Optional[str] = None
    updateDate: Optional[str] = None
