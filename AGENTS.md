# AGENTS.md

本文件是给 AI 智能体（Claude Code、Cursor、Copilot、Hermes 等）的项目接入说明。阅读本文件后，你应能快速理解项目结构、技术栈、模块划分、接口规范与鉴权流程。接口的完整入参/出参文档位于 `docs/api/` 目录。

## 项目概述

- 项目类型：FastAPI 多模块微服务（Python 3.11）
- Web 框架：FastAPI 0.116.1 + Uvicorn 0.35.0
- ORM：SQLAlchemy 2.0.41（异步语法 async/await）
- 注册中心：Nacos（nacos-sdk-python）
- 网关：自研 FastAPI 网关（httpx 反向代理 + JWT 校验 + 异步请求日志）
- 数据库：MySQL（主库名 `play`）、Redis、MongoDB（网关日志）、ChromaDB / Elasticsearch（向量检索）

## 模块列表（服务名 + 端口 + 路径前缀）

| 模块 | 服务名 | 端口 | 网关路径前缀 | 说明 |
|------|--------|------|--------------|------|
| gateway | gateway-service | 4009 | - | 统一入口，路由转发 + JWT 校验 + 异步请求日志 |
| movie | movie-service | 4001 | /service/movie | 电影模块 |
| music | music-service | 4002 | /service/music | 音乐模块 |
| social | social-service | 4003 | /service/social | 评论/点赞社交模块 |
| circle | circle-service | 4004 | /service/circle | 朋友圈（电影圈/音乐圈）模块 |
| user | user-service | 4005 | /service/user | 用户模块 |
| chat | chat-service | 4006 | /service/chat | 聊天/文档/AI 对话模块 |
| tenant | tenant-service | 4007 | /service/tenant | 租户模块 |
| prompt | prompt-service | 4008 | /service/prompt | 提示词模块 |
| agent | agent-service | 4010 | /service/agent | 智能体模块 |
| company | company-service | 4011 | /service/company | 企业模块 |
| common | - | - | - | 公共模块（result_util、数据库连接、jwt_util、nacos_util） |

## 架构与调用规范（重要）

1. **所有客户端请求必须通过 gateway（4009）转发**，禁止直接调用业务模块。
2. **路由规则**：URL 格式 `/service/{模块名}/...`，网关按 `SERVICE_MAPPING` 映射到 `{模块名}-service`（优先本地端口，Nacos 兜底）。
3. **鉴权与身份透传**：
   - 网关 `AuthMiddleware` 读取请求头 `Authorization: Bearer <token>`，用 JWT 解析出 `userId`，写入请求头 `X-User-Id` 透传给下游。
   - **业务模块禁止再次做 JWT 校验**，统一通过 `current_user_id: str = Depends(get_user_id_from_header)` 获取（`get_user_id_from_header` 从请求头 `X-User-Id` 提取）。
   - WebSocket：token 通过查询参数 `?token=...` 传递，网关解析后把 `X-User-Id` 加入目标 URL 查询参数。
4. **鉴权白名单**（无需 token）：
   - `POST /service/user/register`
   - `POST /service/user/login`
   - `POST /service/user/loginByEmail`
   - `POST /service/user/vertifyUser`
   - `POST /service/user/sendEmailVertifyCode`
   - `POST /service/user/resetPassword`
5. **网关不调用业务模块内部逻辑**，只做路由转发、鉴权、日志。

## 统一接口返回规范

所有接口统一返回 `ResultEntity`（`from common.utils.result_util import ResultEntity, ResultUtil`）：

| 字段 | 类型 | 说明 |
|------|------|------|
| data | Any | 业务数据 |
| status | str | `SUCCESS` / `FAIL` |
| msg | str | 提示信息 |
| total | int | 记录总数（仅分页查询设置） |
| token | str | 用户凭证（仅登录/注册返回） |

- 成功：`ResultUtil.success(data=...)`，分页：`ResultUtil.success(data=..., total=...)`，失败：`ResultUtil.fail(data=None, msg=...)`。
- **字段自动转换**：`ResultUtil.success` 内部通过 `convert_snake_to_camel` 把返回数据中的下划线字段（snake_case）自动转为驼峰（camelCase），无需手动处理。

## 命名规范

- 数据库字段：下划线命名（snake_case），如 `user_name`、`create_time`。
- 接口入参（Request）：驼峰命名（camelCase），如 `relationId`、`pageNum`；Pydantic 模型用 `Field(alias=...)` + `populate_by_name=True` 支持。
- 接口出参（Response）：下划线字段自动转为驼峰（由 ResultUtil 完成）。
- 文件命名：snake_case，如 `user_router.py`、`user_service.py`。
- 类名 PascalCase；方法/变量 snake_case。

## 模块内部标准结构

```
模块名/
├── dependencies/   # 依赖注入、权限校验
├── models/         # SQLAlchemy 数据库模型
├── repositories/   # 数据访问层（CRUD）
├── routers/        # 路由定义（API 端点）
├── schemas/        # Pydantic 请求/响应模型
└── services/       # 业务逻辑层
```

分层原则：router → service → repository → model，使用 async/await 语法。

## 接口文档索引

完整接口文档在 `docs/api/` 目录，按模块拆分：

- [docs/api/README.md](docs/api/README.md) —— 索引 + 公共约定
- [docs/api/gateway.md](docs/api/gateway.md)
- [docs/api/user.md](docs/api/user.md)
- [docs/api/chat.md](docs/api/chat.md)
- [docs/api/agent.md](docs/api/agent.md)
- [docs/api/circle.md](docs/api/circle.md)
- [docs/api/company.md](docs/api/company.md)
- [docs/api/movie.md](docs/api/movie.md)
- [docs/api/music.md](docs/api/music.md)
- [docs/api/prompt.md](docs/api/prompt.md)
- [docs/api/social.md](docs/api/social.md)
- [docs/api/tenant.md](docs/api/tenant.md)

> 快速定位某个接口：先看 `docs/api/README.md` 的接口总表，再进入对应模块文档查看入参/出参详情。
