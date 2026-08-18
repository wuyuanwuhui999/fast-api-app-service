# gateway 网关模块

> 服务名：gateway-service | 端口：4009 | 统一入口

## 概述

自研 FastAPI 网关，是系统唯一对外入口。职责：路由转发、JWT 校验、异步请求日志。**网关不暴露业务接口，也不调用业务模块内部逻辑**，只做反向代理转发。

## 路由规则

URL 格式 `/service/{模块名}/**`，按 `SERVICE_MAPPING` 映射到 `{模块名}-service`（优先本地端口，Nacos 兜底）：

| 路径前缀 | 目标服务 | 端口 |
|----------|----------|------|
| /service/movie/** | movie-service | 4001 |
| /service/music/** | music-service | 4002 |
| /service/social/** | social-service | 4003 |
| /service/circle/** | circle-service | 4004 |
| /service/user/** | user-service | 4005 |
| /service/chat/** | chat-service | 4006 |
| /service/tenant/** | tenant-service | 4007 |
| /service/prompt/** | prompt-service | 4008 |
| /service/agent/** | agent-service | 4010 |
| /service/company/** | company-service | 4011 |

## WebSocket 代理

网关为以下 WebSocket 路径做反向代理（认证通过 `?token=` 参数）：

| WebSocket 路径 | 目标服务 |
|----------------|----------|
| /service/chat/ws/chat | chat-service |
| /service/agent/ws/chat | agent-service |
| /service/circle/ws | circle-service |

## 鉴权（AuthMiddleware）

### HTTP 鉴权流程

1. 白名单路径直接放行（见下表）。
2. 从请求头读取 `Authorization: Bearer <token>`。
3. 用 JWT（`SECRET_KEY` + `ALGORITHM`）解析 token → 从 `sub` 解析出 `id`。
4. 将 `id` 写入请求头 `X-User-Id`（`request.state.user_id`），转发给下游。
5. 无 token / token 无效 → 返回 401。

### 鉴权白名单

| 方法 | 路径 |
|------|------|
| POST | /service/user/register |
| POST | /service/user/login |
| POST | /service/user/loginByEmail |
| POST | /service/user/vertifyUser |
| POST | /service/user/sendEmailVertifyCode |
| POST | /service/user/resetPassword |

### WebSocket 鉴权

1. token 从查询参数 `?token=...` 获取（需 `Bearer ` 前缀）。
2. 解析出 userId 后，把 `X-User-Id` 加入目标 WebSocket URL 的查询参数，转发给下游服务。

## 请求日志（LogMiddleware）

- 记录每个请求/响应（路径、方法、userId、耗时、响应体）。
- 异步写入数据库（`asyncio.create_task`），不阻塞响应。
- 排除 `/health`、`/metrics`、`/favicon.ico`。

## JWT 配置（环境变量）

- `SECRET_KEY`、`ALGORITHM`（默认 HS256）
- `ACCESS_TOKEN_EXPIRE_MINUTES`
