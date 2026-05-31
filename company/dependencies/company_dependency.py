from fastapi import Depends, HTTPException, Header
from typing import Optional


def get_user_id_from_header(x_user_id: str = Header(None, alias="X-User-Id")):
    """从网关传递的header中获取用户ID"""
    if not x_user_id:
        raise HTTPException(status_code=401, detail="未提供用户标识")
    return x_user_id


def get_company_permission(
    company_id: str,
    required_role: int = 1,
    current_user_id: str = Depends(get_user_id_from_header),
    company_service: Optional = None
):
    """
    企业权限依赖注入
    
    Args:
        company_id: 企业ID
        required_role: 所需的最低角色（1-管理员，2-人事，3-老板）
        current_user_id: 当前用户ID
        company_service: 企业服务实例
    """
    async def dependency():
        if not company_service:
            raise HTTPException(status_code=500, detail="服务未初始化")
        
        user_role = await company_service.get_user_role_in_company(company_id, current_user_id)
        if user_role < required_role:
            raise HTTPException(status_code=403, detail="权限不足")
        
        return user_role
    
    return dependency