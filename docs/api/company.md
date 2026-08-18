# company 企业模块接口文档

> 服务名：company-service | 端口：4011 | 路径前缀：/service/company

## 概述

企业模块：企业列表、企业成员管理（列表/搜索/添加/移除/角色）、部门、职位。

## 鉴权

除 `getPositions` 外，其余接口均需 token（网关注入 `X-User-Id`）。

## 接口总览

| 方法 | 接口 | 作用 | 鉴权 |
|------|------|------|------|
| GET | /service/company/getCompanyList | 用户所属公司列表 | 需 |
| GET | /service/company/getCompanyUsers | 公司成员列表 | 需 |
| GET | /service/company/searchUsers | 搜索公司用户 | 需 |
| POST | /service/company/addUser | 添加用户到公司 | 需 |
| PUT | /service/company/updateUserRole | 修改用户角色 | 需 |
| DELETE | /service/company/removeUser | 移除用户 | 需 |
| GET | /service/company/getDepartments | 查公司部门 | 需 |
| GET | /service/company/getPositions | 查部门职位 | 否 |

> 差异：Spring Boot 无 `updateUserRole`、`removeUser`，FastAPI 新增这两个接口。

## 接口详情

### 1. 用户所属公司列表
- 接口：`GET /service/company/getCompanyList`
- 入参：`X-User-Id`（Header）
- 出参：ResultEntity，data 为公司列表

### 2. 公司成员列表
- 接口：`GET /service/company/getCompanyUsers`
- 作用：分页查询企业成员（需企业管理员权限）
- 入参：`X-User-Id`（Header）+ Query：`companyId`、`pageNum`（默认 1）、`pageSize`（默认 10）、`keyword`（可选）
- 出参：ResultEntity，data 为成员列表，`total` 为总数

### 3. 搜索公司用户
- 接口：`GET /service/company/searchUsers`
- 入参：`X-User-Id`（Header）+ Query：`companyId`、`pageNum`、`pageSize`、`keyword`（可选）
- 出参：ResultEntity，data 为用户列表，`total` 为总数

### 4. 添加用户到公司
- 接口：`POST /service/company/addUser`
- 入参：`X-User-Id`（Header）+ Body（AddCompanyUserSchema）
- 出参：ResultEntity

### 5. 修改用户角色
- 接口：`PUT /service/company/updateUserRole`
- 作用：修改用户在企业中的角色（role=2 超管可改 0/1，role=1 管理员可改 0）
- 入参：`X-User-Id`（Header）+ Body（UpdateUserRoleSchema）
- 出参：ResultEntity

### 6. 移除用户
- 接口：`DELETE /service/company/removeUser`
- 入参：`X-User-Id`（Header）+ Body（RemoveUserSchema）
- 出参：ResultEntity

### 7. 查公司部门
- 接口：`GET /service/company/getDepartments`
- 入参：`X-User-Id`（Header）+ Query：`companyId`
- 出参：ResultEntity，data 为部门列表

### 8. 查部门职位
- 接口：`GET /service/company/getPositions`
- 入参（Query）：`departmentId`
- 出参：ResultEntity，data 为职位列表

## 请求体实体字段

**AddCompanyUserSchema**

| 字段 | 类型 | 说明 |
|------|------|------|
| userId | str | 用户 ID |
| companyId | str | 企业 ID |
| positionId | str | 职位 ID |
| departmentId | str | 部门 ID |
| role | int | 角色（2 超管 / 1 管理员 / 0 普通成员） |

**UpdateUserRoleSchema**：`userId`、`companyId`、`role`

**RemoveUserSchema**：`userId`、`companyId`
