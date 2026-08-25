# user 用户模块接口文档

> 服务名：user-service | 端口：4005 | 路径前缀：/service/user

## 概述

用户模块：注册、登录、邮箱登录、校验用户、用户信息查询/更新、改密码、头像上传、邮箱验证码、重置密码、搜索用户。

## 鉴权

- 白名单（无需 token）：register / login / loginByEmail / vertifyUser / sendEmailVertifyCode / resetPassword。
- 其余接口需 token，经网关注入 `X-User-Id`，通过 `Depends(get_user_id_from_header)` 获取。

## 接口总览

| 方法 | 接口 | 作用 | 鉴权 |
|------|------|------|------|
| POST | /service/user/register | 注册 | 白名单 |
| POST | /service/user/login | 登录 | 白名单 |
| GET | /service/user/getUserData | 查询用户信息（返回新 token） | 需 |
| PUT | /service/user/updateUser | 更新用户信息 | 需 |
| PUT | /service/user/updatePassword | 修改密码 | 需 |
| POST | /service/user/sendEmailVertifyCode | 发送邮箱验证码 | 白名单 |
| POST | /service/user/resetPassword | 重置密码 | 白名单 |
| POST | /service/user/loginByEmail | 邮箱登录 | 白名单 |
| POST | /service/user/vertifyUser | 校验用户是否存在 | 白名单 |
| GET | /service/user/searchUsers | 搜索用户 | 需 |
| POST | /service/user/updateAvater | 头像上传 | 需 |

> 差异：`searchUsers` 参数为 `tenantId`（Spring 为 `companyId`）；`updateAvater` 路径为 `/service/user/updateAvater`（Spring 源码为 `/service/updateAvater`，属 bug 已修正）。

## 接口详情

### 1. 注册
- 接口：`POST /service/user/register`
- 作用：注册新用户
- 入参（Body，UserCreate）：`userAccount`、`password`、`username` 等
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 2. 登录
- 接口：`POST /service/user/login`
- 作用：账号密码登录
- 入参（Body，LoginForm）：`userAccount`（账号）、`password`（密码）
- 出参：ResultEntity，`token` 为登录凭证
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.xxx"
}
```

### 3. 查询用户信息
- 接口：`GET /service/user/getUserData`
- 作用：查询当前登录用户信息，并签发新 token
- 入参：`X-User-Id`（Header）
- 出参：ResultEntity，data 为用户信息，`token` 为新签发的凭证
- 出参示例：
```json
{
  "data": {"id":"uuid","userAccount":"user123","username":"昵称","telephone":"13800138000","email":"user@example.com","avater":"https://example.com/avatar.jpg","birthday":"1990-01-01","sex":"0","role":"admin","sign":"个性签名","region":"广东","disabled":0,"permission":1},
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.xxx"
}
```

### 4. 更新用户信息
- 接口：`PUT /service/user/updateUser`
- 作用：更新当前用户资料
- 入参：`X-User-Id`（Header）+ Body（UserUpdate）
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 5. 修改密码
- 接口：`PUT /service/user/updatePassword`
- 作用：修改登录密码
- 入参：`X-User-Id`（Header）+ Body（PasswordChange：`oldPassword`、`newPassword`）
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 6. 发送邮箱验证码
- 接口：`POST /service/user/sendEmailVertifyCode`
- 作用：找回密码/邮箱登录时发送验证码
- 入参（Body，MailRequest）：`email` 等
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 7. 重置密码
- 接口：`POST /service/user/resetPassword`
- 作用：通过邮箱验证码重置密码
- 入参（Body，ResetPasswordConfirm）：`email`、`code`（验证码）、`password`（新密码）
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 8. 邮箱登录
- 接口：`POST /service/user/loginByEmail`
- 作用：邮箱验证码登录
- 入参（Body，MailRequest）：`email`、`code`（验证码）
- 出参：ResultEntity，`token` 为登录凭证
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyMTIzIn0.xxx"
}
```

### 9. 校验用户是否存在
- 接口：`POST /service/user/vertifyUser`
- 作用：注册前校验账号/用户名是否已存在
- 入参（Body，UserCreate）：`userAccount` 或 `username`
- 出参：ResultEntity
- 出参示例：
```json
{
  "data": null,
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

### 10. 搜索用户
- 接口：`GET /service/user/searchUsers`
- 作用：按关键字模糊搜索用户（分页）
- 入参（Query）：`keyword`（必填）、`tenantId`（默认空）、`pageNum`（默认 1）、`pageSize`（默认 100）
- 出参：ResultEntity，data 为用户列表，`total` 为总数
- 出参示例：
```json
{
  "data": [{"id":"uuid","userAccount":"user123","username":"昵称","telephone":"13800138000","email":"user@example.com","avater":"https://example.com/avatar.jpg","birthday":"1990-01-01","sex":"0","role":"admin","sign":"个性签名","region":"广东","disabled":0,"permission":1}],
  "status": "SUCCESS",
  "msg": null,
  "total": 100,
  "token": null
}
```

### 11. 头像上传
- 接口：`POST /service/user/updateAvater`
- 作用：上传头像图片
- 入参：`X-User-Id`（Header）+ Form：`file`（multipart/form-data 文件，支持 jpg/jpeg/png/gif/bmp）
- 出参：ResultEntity，data 为新头像 URL
- 出参示例：
```json
{
  "data": "https://example.com/avatar2.jpg",
  "status": "SUCCESS",
  "msg": null,
  "total": null,
  "token": null
}
```

## 请求体实体字段

**UserCreate / UserUpdate**（用户注册/更新）

| 字段 | 类型 | 说明 |
|------|------|------|
| userAccount | str | 账号 |
| username | str | 昵称 |
| password | str | 密码 |
| telephone | str | 电话 |
| email | str | 邮箱 |
| avater | str | 头像 |
| sex | str | 性别 |
| birthday | str | 出生年月日 |
| sign | str | 个性签名 |
| region | str | 地区 |

**PasswordChange**

| 字段 | 类型 | 说明 |
|------|------|------|
| oldPassword | str | 旧密码 |
| newPassword | str | 新密码 |

## 涉及的表结构

> 数据库：MySQL `127.0.0.1:3306/play`（root）。以下为本模块接口读写涉及的表结构。

### 1. user（用户表）

| 字段 | 类型 | 空 | 键 | 说明 |
|------|------|-----|------|------|
| id | varchar(32) | 否 |  | 主键id |
| user_account | varchar(32) | 否 |  | 账号 |
| password | varchar(255) | 否 |  | 密码 |
| create_date | varchar(255) | 否 |  | 创建时间 |
| update_date | datetime | 否 |  | 更新时间 |
| username | varchar(255) | 否 |  | 昵称 |
| telephone | varchar(20) | 否 |  | 电话 |
| email | varchar(255) | 否 |  | 邮箱 |
| avater | varchar(255) | 是 |  | 头像地址 |
| birthday | varchar(16) | 是 |  | 出生年月日 |
| sex | varchar(1) | 是 |  | 性别，0:男，1:女 |
| role | varchar(255) | 是 |  | 角色 |
| sign | varchar(255) | 是 |  | 个性签名 |
| region | varchar(255) | 是 |  | 地区 |
| disabled | int | 是 |  | 是否禁用，0表示不不禁用，1表示禁用 |
| permission | int | 是 |  | 权限大小 |

### 2. login_log（登录日志表）

| 字段 | 类型 | 空 | 键 | 说明 |
|------|------|-----|------|------|
| id | bigint | 否 | 主键 | 主键ID（自增） |
| user_id | varchar(50) | 是 | 索引 | 用户ID |
| ip | varchar(50) | 是 |  | 登录IP |
| login_type | varchar(50) | 是 |  | 登录类型：register/login/getUserData |
| create_time | datetime | 是 | 索引 | 登录时间 |

