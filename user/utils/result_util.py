from typing import Optional, Any
from pydantic import BaseModel, Field
import re

class ResultEntity(BaseModel):
    data: Optional[Any] = Field(None, description="数据（可为None）")  # 明确表示可以是None
    status: str = Field("SUCCESS", description="状态")
    msg: Optional[str] = Field(None, description="信息")
    total: Optional[int] = Field(None, description="总页数")
    token: Optional[str] = Field(None, description="token")

class ResultUtil:
    @staticmethod
    def success(
        data: Optional[Any] = None,
        camel_data: Optional[Any] = None,# 驼峰写法
        msg: Optional[str] = None,
        total: Optional[int] = None,
        token: Optional[str] = None
    ) -> ResultEntity:
        """
        成功的返回数据
        :param data: 返回数据
        :param msg: 可选的消息
        :param total: 可选的总数
        :param token: 可选的token
        :return: ResultEntity
        """
        print(camel_data)
        print(ResultUtil.convert_snake_to_camel(data))
        return ResultEntity(
            data=camel_data if camel_data is not None else ResultUtil.convert_snake_to_camel(data),
            status="SUCCESS",
            msg=msg,
            total=total,
            token=token
        )

    @staticmethod
    def fail(
        data: Optional[Any],  # 必须参数但允许None
        msg: Optional[str] = None,
        status_code: str = "FAIL"
    ) -> ResultEntity:
        """
        失败的返回数据
        :param data: 必须的返回数据（但可以显式传None）
        :param msg: 可选的消息
        :param status_code: 可选的状态码，默认为"FAIL"
        :return: ResultEntity
        """
        return ResultEntity(
            data=ResultUtil.convert_snake_to_camel(data),
            status=status_code,
            msg=msg
        )

    @staticmethod
    def convert_snake_to_camel(data: Any) -> Any:
        """将下划线命名转换为驼峰命名（自动处理None值）"""
        if data is None:
            return None
        if isinstance(data, dict):
            return {ResultUtil.snake_to_camel(k): ResultUtil.convert_snake_to_camel(v)
                   for k, v in data.items()}
        elif isinstance(data, (list, tuple)):
            return [ResultUtil.convert_snake_to_camel(item) for item in data]
        return data

    @staticmethod
    def snake_to_camel(snake_str: str) -> str:
        """下划线转驼峰"""
        components = snake_str.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])