from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List


class ChatSchema(BaseModel):
    id: Optional[int] = None
    user_id: str
    tenant_id: Optional[str] = None
    files: Optional[str] = None
    chat_id: str
    prompt: str
    system_prompt: Optional[str] = None
    model_id: str
    content: Optional[str] = None
    think_content: Optional[str] = None
    response_content: Optional[str] = None
    create_time: Optional[datetime] = None

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
    """WebSocket消息参数 - 通过send方法传递"""
    prompt: str
    systemPrompt: Optional[str] = None
    docIds: Optional[List[str]] = None
    chatId: str
    modelId: str
    showThink: bool = False
    type: Optional[str] = None
    language: Optional[str] = None
    companyId: str
    tenantId: Optional[str] = None


class ClientMessage(BaseModel):
    chat_id: str
    prompt: str
    files: List[str]


class DirectorySchema(BaseModel):
    id: str
    user_id: str
    directory: str
    tenant_id: str
    update_time: Optional[str] = None
    create_time: Optional[str] = None

    class Config:
        from_attributes = True


class ChatModelSchema(BaseModel):
    id: str
    type: str
    api_key: Optional[str] = None
    model_name: str
    base_url: Optional[str] = None
    company_id: Optional[str] = Field(None, alias="companyId")
    created_by: Optional[str] = Field(None, alias="createdBy")  # 新增字段
    disabled: int = 0
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S")
        }
    )


class ChatDocSchema(BaseModel):
    """文档Schema - 完整字段定义"""
    id: str
    directory_id: Optional[str] = None
    doc_id: Optional[str] = None
    name: Optional[str] = None
    ext: Optional[str] = None
    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.strftime("%Y-%m-%d %H:%M:%S") if v else None
        }
    )


class CreateDirectoryShema(BaseModel):
    directory: str
    tenantId: str


class RenameDirectorySchema(BaseModel):
    """重命名目录请求Schema"""
    id: str = Field(..., description="目录ID")
    directory: str = Field(..., description="新目录名称")
    tenantId: Optional[str] = Field(None, description="租户ID（可选）")

    model_config = ConfigDict(populate_by_name=True)


# ==================== 新增模型管理 Schema ====================

class AddModelSchema(BaseModel):
    """添加模型请求Schema"""
    modelName: str = Field(..., description="模型名称")
    type: str = Field(..., description="模型类型：ollama/deepseek/tongyi")
    companyId: str = Field(..., description="企业ID")
    apiKey: Optional[str] = Field(None, description="API密钥（在线模型需要）")
    baseUrl: str = Field(..., description="API基础URL")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "modelName": "deepseek-chat",
                "type": "deepseek",
                "companyId": "abc123def456",
                "apiKey": "sk-xxx",
                "baseUrl": "https://api.deepseek.com/v1"
            }
        }
    )


class UpdateModelSchema(BaseModel):
    """更新模型请求Schema"""
    id: str = Field(..., description="模型ID")
    modelName: str = Field(..., description="模型名称")
    type: str = Field(..., description="模型类型：ollama/deepseek/tongyi")
    companyId: str = Field(..., description="企业ID")
    apiKey: Optional[str] = Field(None, description="API密钥（在线模型需要）")
    baseUrl: str = Field(..., description="API基础URL")

    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "id": "model_123456",
                "modelName": "deepseek-chat",
                "type": "deepseek",
                "companyId": "abc123def456",
                "apiKey": "sk-xxx",
                "baseUrl": "https://api.deepseek.com/v1"
            }
        }
    )