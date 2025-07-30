from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List

class ChatEntity(BaseModel):
    id: Optional[int] = None
    user_id: str
    files: Optional[str] = None
    chat_id: str
    prompt: str
    model_name: str
    content: Optional[str] = None
    think_content: Optional[str] = None
    response_content: Optional[str] = None
    create_time: Optional[str] = None

    # 自定义内容处理方法
    def set_content(self, content: str):
        self.content = content

        if not content:
            self.think_content = None
            self.response_content = None
            return

        think_start = content.find("<think>")
        think_end = content.find("</think>")

        if think_start >= 0 and think_end > think_start:
            self.think_content = content[think_start:think_end + len("</think>")]
            after_think = content[think_end + len("</think>"):]
            self.response_content = after_think.strip()
        else:
            self.think_content = None
            self.response_content = content

class ChatParamsEntity(BaseModel):
    prompt: str
    directory_id: str = "public"
    chat_id: str
    model_name: str
    show_think: bool = False
    type: Optional[str] = None  # document/db
    language: Optional[str] = None  # zh/cn

class ClientMessage(BaseModel):
    chat_id: str
    prompt: str
    token: str
    files: List[str]

class DirectoryEntity(BaseModel):
    id: str
    user_id: str
    directory: str
    update_time: Optional[str] = None
    create_time: Optional[str] = None

    class Config:
        from_attributes = True  # 允许ORM模型转换