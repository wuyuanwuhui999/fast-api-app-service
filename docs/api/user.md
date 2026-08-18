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

### 2. 登录
- 接口：`POST /service/user/login`
- 作用：账号密码登录
- 入参（Body，LoginForm）：`userAccount`（账号）、`password`（密码）
- 出参：ResultEntity，`token` 为登录凭证

### 3. 查询用户信息
- 接口：`GET /service/user/getUserData`
- 作用：查询当前登录用户信息，并签发新 token
- 入参：`X-User-Id`（Header）
- 出参：ResultEntity，data 为用户信息，`token` 为新签发的凭证

### 4. 更新用户信息
- 接口：`PUT /service/user/updateUser`
- 作用：更新当前用户资料
- 入参：`X-User-Id`（Header）+ Body（UserUpdate）
- 出参：ResultEntity

### 5. 修改密码
- 接口：`PUT /service/user/updatePassword`
- 作用：修改登录密码
- 入参：`X-User-Id`（Header）+ Body（PasswordChange：`oldPassword`、`newPassword`）
- 出参：ResultEntity

### 6. 发送邮箱验证码
- 接口：`POST /service/user/sendEmailVertifyCode`
- 作用：找回密码/邮箱登录时发送验证码
- 入参（Body，MailRequest）：`email` 等
- 出参：ResultEntity

### 7. 重置密码
- 接口：`POST /service/user/resetPassword`
- 作用：通过邮箱验证码重置密码
- 入参（Body，ResetPasswordConfirm）：`email`、`code`（验证码）、`password`（新密码）
- 出参：ResultEntity

### 8. 邮箱登录
- 接口：`POST /service/user/loginByEmail`
- 作用：邮箱验证码登录
- 入参（Body，MailRequest）：`email`、`code`（验证码）
- 出参：ResultEntity，`token` 为登录凭证

### 9. 校验用户是否存在
- 接口：`POST /service/user/vertifyUser`
- 作用：注册前校验账号/用户名是否已存在
- 入参（Body，UserCreate）：`userAccount` 或 `username`
- 出参：ResultEntity

### 10. 搜索用户
- 接口：`GET /service/user/searchUsers`
- 作用：按关键字模糊搜索用户（分页）
- 入参（Query）：`keyword`（必填）、`tenantId`（默认空）、`pageNum`（默认 1）、`pageSize`（默认 100）
- 出参：ResultEntity，data 为用户列表，`total` 为总数

### 11. 头像上传
- 接口：`POST /service/user/updateAvater`
- 作用：上传头像图片
- 入参：`X-User-Id`（Header）+ Form：`file`（multipart/form-data 文件，支持 jpg/jpeg/png/gif/bmp）
- 出参：ResultEntity，data 为新头像 URL

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
