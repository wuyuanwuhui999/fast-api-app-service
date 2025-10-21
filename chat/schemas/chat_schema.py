from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional, List


class ChatSchema(BaseModel):
    id: Optional[int] = None
    user_id: str
    files: Optional[str] = None
    chat_id: str
    prompt: str
    system_prompt: Optional[str] = None
    model_name: str
    content: Optional[str] = None
    think_content: Optional[str] = None
    response_content: Optional[str] = None
    create_time: Optional[datetime] = None  # 改为 datetime 类型

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
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )

class ChatParamsEntity(BaseModel):
    prompt: str
    systemPrompt: Optional[str] = None
    directoryId: str = "default"
    chatId: str
    token: str
    modelId: str  # 改为modelId
    showThink: bool = False
    type: Optional[str] = None  # document/db
    language: Optional[str] = None  # zh/cn
    tenant_id: Optional[str] = None

class ClientMessage(BaseModel):
    chat_id: str
    prompt: str
    token: str
    files: List[str]


class DirectorySchema(BaseModel):
    id: str
    user_id: str
    directory: str
    tenant_id: str
    update_time: Optional[str] = None
    create_time: Optional[str] = None

    class Config:
        from_attributes = True  # 允许ORM模型转换


class ChatModelSchema(BaseModel):
    id: str
    type: str
    api_key: Optional[str] = None
    model_name: str
    base_url: Optional[str] = None
    disabled: int = 0  # 新增disabled字段
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
    tenant_id: Optional[str] = None  # 新增tenant_id字段
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

class CreateDirectoryShema(BaseModel):
    directory: str
    tenantId: str
