# circle/services/circle_service.py
import os
import re
import uuid
from typing import Optional

from fastapi import Depends
from sqlalchemy.orm import Session
from fastapi.logger import logger

from common.config.common_database import get_db
from common.utils.result_util import ResultEntity, ResultUtil
from circle.models.circle_model import Circle
from circle.repositories.circle_repository import CircleRepository
from circle.schemas.circle_schema import InsertCircleSchema
from circle.utils.circle_util import generate_image
from circle.websocket_manager import manager

# 朋友圈图片保存目录（文件系统绝对路径），对应 Spring 中 static.upload-path
CIRCLE_UPLOAD_PATH = os.getenv("CIRCLE_UPLOAD_PATH", "/Users/wuwenqiang/Documents/static/circle")
# 返回给前端的图片 URL 前缀
CIRCLE_IMG_PREFIX = "/static/circle/"


class CircleService:
    """朋友圈业务逻辑层"""

    def __init__(self, db: Session = Depends(get_db)):
        self.repository = CircleRepository(db)

    async def get_circle_list_by_type(
            self,
            page_num: int,
            page_size: int,
            circle_type: str
    ) -> ResultEntity:
        """分页获取朋友圈列表"""
        try:
            if page_num < 1:
                page_num = 1
            if page_size < 1:
                page_size = 10

            start = (page_num - 1) * page_size
            circle_list = self.repository.get_circle_list_by_type(start, page_size, circle_type)
            total = self.repository.get_circle_count(circle_type)

            return ResultUtil.success(data=circle_list, total=total)
        except Exception as e:
            logger.error(f"获取朋友圈列表失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取朋友圈列表失败: {str(e)}", data=None)

    async def get_circle_article_count(self, circle_id: int) -> ResultEntity:
        """获取文章的评论数、浏览数、收藏数"""
        try:
            if circle_id <= 0:
                return ResultUtil.fail(msg="文章ID不能为空", data=None)
            data = self.repository.get_circle_article_count(circle_id)
            return ResultUtil.success(data=data)
        except Exception as e:
            logger.error(f"获取朋友圈文章计数失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取朋友圈文章计数失败: {str(e)}", data=None)

    async def insert_circle(self, circle_data: InsertCircleSchema, user_id: str) -> ResultEntity:
        """新增朋友圈（保存图片、广播 WebSocket 消息）"""
        try:
            if not circle_data.content or not circle_data.content.strip():
                return ResultUtil.fail(msg="朋友圈内容不能为空", data=None)

            if not circle_data.type or not circle_data.type.strip():
                return ResultUtil.fail(msg="朋友圈类型不能为空", data=None)

            imgs = self._process_images(circle_data.imgs)

            circle = Circle(
                content=circle_data.content,
                imgs=imgs,
                relation_id=circle_data.relation_id,
                type=circle_data.type,
                user_id=user_id,
                permission=circle_data.permission,
            )

            inserted = self.repository.insert_circle(circle)

            # 广播新消息通知
            await manager.broadcast("有一条新消息")

            return ResultUtil.success(data=inserted.id)
        except Exception as e:
            logger.error(f"新增朋友圈失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"新增朋友圈失败: {str(e)}", data=None)

    async def get_circle_by_last_update_time(
            self,
            last_update_time: str,
            circle_type: str
    ) -> ResultEntity:
        """获取最近更新的朋友圈数量"""
        try:
            count = self.repository.get_circle_by_last_update_time(last_update_time, circle_type)
            return ResultUtil.success(data=count)
        except Exception as e:
            logger.error(f"获取朋友圈最近更新数量失败: {str(e)}", exc_info=True)
            return ResultUtil.fail(msg=f"获取朋友圈最近更新数量失败: {str(e)}", data=None)

    def _process_images(self, imgs: Optional[str]) -> Optional[str]:
        """
        处理 base64 图片，保存到磁盘并返回逗号分隔的 URL 列表

        与 Spring CircleService.insertCircle 中的逻辑对齐：
        - 逗号分隔多张 base64 图片
        - 解析扩展名、去除 data:image/xxx;base64, 前缀
        - UUID 命名，保存后追加尺寸后缀
        """
        if not imgs:
            return imgs

        base64_imgs = imgs.split(",")
        saved_urls = []

        for base64_item in base64_imgs:
            if not base64_item:
                continue
            # 解析扩展名：data:image/png;base64,xxx -> png
            ext = re.sub(r";base64,.+", "", base64_item)
            ext = re.sub(r"data:image/", "", ext)
            if not ext:
                ext = "png"
            # 去除前缀：data:image/xxx;base64, -> 纯 base64
            pure_base64 = re.sub(r"data:image/.+base64,", "", base64_item)

            img_name = uuid.uuid4().hex + "." + ext
            save_path = os.path.join(CIRCLE_UPLOAD_PATH, img_name)
            url = generate_image(pure_base64, save_path, CIRCLE_IMG_PREFIX)
            if url:
                saved_urls.append(url)

        return ",".join(saved_urls)
