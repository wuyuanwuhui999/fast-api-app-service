# FastAPI 微服务接口文档

本目录存放项目全部模块的接口文档。所有接口统一经 `gateway`（端口 4009）转发访问，不直接调用业务模块。

## 公共约定

### 请求入口

- 统一入口：`http://<gateway-host>:4009`
- URL 格式：`/service/{模块名}/{接口路径}`

### 鉴权流程（Gateway → 业务模块）

```
客户端 ──(Authorization: Bearer <token>)──> gateway
  gateway: AuthMiddleware 解析 token → userId
  gateway: 将 userId 放入请求头 X-User-Id → 转发
业务模块: current_user_id = Depends(get_user_id_from_header)  # 从 X-User-Id 提取
```

- HTTP 请求：`Authorization: Bearer <token>` 头。
- WebSocket 连接：`?token=<token>` 查询参数。

### 鉴权白名单（无需 token）

| 方法 | 接口 | 作用 |
|------|------|------|
| POST | /service/user/register | 注册 |
| POST | /service/user/login | 登录 |
| POST | /service/user/loginByEmail | 邮箱登录 |
| POST | /service/user/vertifyUser | 校验用户是否存在 |
| POST | /service/user/sendEmailVertifyCode | 发送邮箱验证码 |
| POST | /service/user/resetPassword | 重置密码 |

### 统一返回结构 ResultEntity

```json
{
  "data": {},        // 业务数据（下划线字段已自动转驼峰）
  "status": "SUCCESS", // SUCCESS / FAIL
  "msg": null,       // 提示信息
  "total": null,     // 分页总记录数
  "token": null      // 登录/注册时返回的凭证
}
```

### 入参位置说明

- `Header`：请求头（`X-User-Id` 由网关注入，前端无需传）
- `Query`：URL 查询参数（如 `?pageNum=1`）
- `Path`：URL 路径参数（如 `/getStar/{movieId}`）
- `Body`：请求体 JSON（Pydantic 模型）
- `Form`：multipart/form-data 文件上传

## 模块接口总表

| 模块 | 服务名 | 端口 | 前缀 | 接口数 | 文档 |
|------|--------|------|------|--------|------|
| gateway | gateway-service | 4009 | - | -（网关） | [gateway.md](gateway.md) |
| user | user-service | 4005 | /service/user | 11 | [user.md](user.md) |
| chat | chat-service | 4006 | /service/chat | 16 | [chat.md](chat.md) |
| agent | agent-service | 4010 | /service/agent | 2 | [agent.md](agent.md) |
| circle | circle-service | 4004 | /service/circle | 5 | [circle.md](circle.md) |
| company | company-service | 4011 | /service/company | 8 | [company.md](company.md) |
| movie | movie-service | 4001 | /service/movie | 23 | [movie.md](movie.md) |
| music | music-service | 4002 | /service/music | 23 | [music.md](music.md) |
| prompt | prompt-service | 4008 | /service/prompt | 5 | [prompt.md](prompt.md) |
| social | social-service | 4003 | /service/social | 8 | [social.md](social.md) |
| tenant | tenant-service | 4007 | /service/tenant | 12 | [tenant.md](tenant.md) |

## 接口快速索引（按模块）

### user（用户）
| 方法 | 接口 | 作用 |
|------|------|------|
| POST | /service/user/register | 注册 |
| POST | /service/user/login | 登录 |
| GET | /service/user/getUserData | 查询用户信息（返回新 token） |
| PUT | /service/user/updateUser | 更新用户信息 |
| PUT | /service/user/updatePassword | 修改密码 |
| POST | /service/user/sendEmailVertifyCode | 发送邮箱验证码 |
| POST | /service/user/resetPassword | 重置密码 |
| POST | /service/user/loginByEmail | 邮箱登录 |
| POST | /service/user/vertifyUser | 校验用户是否存在 |
| GET | /service/user/searchUsers | 搜索用户 |
| POST | /service/user/updateAvater | 头像上传 |

### chat（聊天/文档/模型）
| 方法 | 接口 | 作用 |
|------|------|------|
| POST | /service/chat/chat | AI 对话（HTTP 流式） |
| GET | /service/chat/getChatHistory | 分页聊天历史 |
| GET | /service/chat/getChatHistoryByChatId | 按会话查历史 |
| GET | /service/chat/getModelList | 模型列表 |
| POST | /service/chat/addModel | 新增模型 |
| PUT | /service/chat/updateModel | 更新模型 |
| DELETE | /service/chat/deleteModel/{modelId} | 删除模型 |
| WS | /service/chat/ws/chat | WebSocket 聊天 |
| POST | /service/chat/uploadDoc/{tenantId}/{directoryId} | 上传文档 |
| GET | /service/chat/getDocListByDirId | 按目录查文档 |
| GET | /service/chat/getDocList | 按租户查文档 |
| DELETE | /service/chat/deleteDoc/{doc_id} | 删除文档 |
| GET | /service/chat/getDirectoryList | 目录列表 |
| POST | /service/chat/createDir | 创建目录 |
| PUT | /service/chat/renameDir | 重命名目录 |
| PUT | /service/chat/deleteDir/{directoryId} | 删除目录 |

### agent（智能体）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/agent/getChatHistory | 分页聊天历史 |
| WS | /service/agent/ws/chat | WebSocket 聊天 |

### circle（朋友圈）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/circle/getCircleListByType | 分页朋友圈列表 |
| GET | /service/circle/getCircleArticleCount | 文章评论/收藏/浏览数 |
| POST | /service/circle/insertCircle | 发布朋友圈 |
| GET | /service/circle/getCircleByLastUpdateTime | 最近更新数量 |
| WS | /service/circle/ws | WebSocket 广播 |

### company（企业）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/company/getCompanyList | 用户所属公司列表 |
| GET | /service/company/getCompanyUsers | 公司成员列表 |
| GET | /service/company/searchUsers | 搜索公司用户 |
| POST | /service/company/addUser | 添加用户到公司 |
| PUT | /service/company/updateUserRole | 修改用户角色 |
| DELETE | /service/company/removeUser | 移除用户 |
| GET | /service/company/getDepartments | 查公司部门 |
| GET | /service/company/getPositions | 查部门职位 |

### movie（电影）
23 个接口，见 [movie.md](movie.md)。

### music（音乐）
23 个接口，见 [music.md](music.md)。

### prompt（提示词）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/prompt/getPrompt | 查提示词 |
| GET | /service/prompt/getPromptList | 分页提示词列表 |
| POST | /service/prompt/insertPrompt | 新增提示词 |
| DELETE | /service/prompt/deletePrompt/{promptId}/{tenantId} | 删除提示词 |
| PUT | /service/prompt/updatePrompt | 更新提示词 |

### social（社交评论/点赞）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/social/getCommentCount | 评论总数 |
| GET | /service/social/getTopCommentList | 一级评论列表 |
| GET | /service/social/getReplyCommentList | 回复列表 |
| POST | /service/social/insertComment | 新增评论 |
| DELETE | /service/social/deleteComment/{id} | 删除评论 |
| POST | /service/social/saveLike | 点赞/收藏 |
| DELETE | /service/social/deleteLike | 取消点赞 |
| GET | /service/social/isLike | 是否已点赞 |

### tenant（租户）
| 方法 | 接口 | 作用 |
|------|------|------|
| GET | /service/tenant/getTenantList | 租户列表 |
| GET | /service/tenant/getTenantUser | 当前租户用户信息 |
| GET | /service/tenant/getTenantUserList | 租户用户列表 |
| POST | /service/tenant/create_tenant | 创建租户 |
| PUT | /service/tenant/update_tenant/{tenant_id} | 更新租户 |
| DELETE | /service/tenant/delete_tenant/{tenant_id} | 删除租户 |
| POST | /service/tenant/addTenantUser/{tenant_id}/{user_id} | 添加租户用户 |
| GET | /service/tenant/get_tenant_users/{tenant_id} | 租户下所有用户 |
| POST | /service/tenant/addAdmin/{tenantId}/{userId} | 设为管理员 |
| PUT | /service/tenant/cancelAdmin/{tenantId}/{userId} | 取消管理员 |
| DELETE | /service/tenant/deleteTenantUser/{tenantId}/{userId} | 删除租户用户 |
| GET | /service/tenant/searchTenantUsers | 搜索租户用户 |
