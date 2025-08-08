from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ChatSchema(BaseModel):
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

        if 0 <= think_start < think_end:
            self.think_content = content[think_start:think_end + len("</think>")]
            after_think = content[think_end + len("</think>"):]
            self.response_content = after_think.strip()
        else:
            self.think_content = None
            self.response_content = content

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


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


class DirectorySchema(BaseModel):
    id: str
    user_id: str
    directory: str
    update_time: Optional[str] = None
    create_time: Optional[str] = None

    class Config:
        from_attributes = True  # 允许ORM模型转换


class ChatModelSchema(BaseModel):
    id: int
    model_name: Optional[str] = None  # 替代 str | None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


class ChatDocSchema(BaseModel):
    id: str
    directory_id: Optional[str] = None
    name: Optional[str] = None
    ext: Optional[str] = None
    user_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None
