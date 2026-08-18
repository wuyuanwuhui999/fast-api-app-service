# chat 聊天模块接口文档

> 服务名：chat-service | 端口：4006 | 路径前缀：/service/chat

## 概述

聊天模块：AI 对话（WebSocket 流式）、聊天历史、文档上传/删除、目录管理、模型管理。

## 鉴权

除 `getModelList` 外，其余接口均需 token（网关注入 `X-User-Id`）；WebSocket 通过 `?token=` 参数。

## 接口总览

| 方法 | 接口 | 作用 | 鉴权 |
|------|------|------|------|
| POST | /service/chat/chat | AI 对话（HTTP 流式） | 需 |
| GET | /service/chat/getChatHistory | 分页聊天历史 | 需 |
| GET | /service/chat/getChatHistoryByChatId | 按会话查历史 | 需 |
| GET | /service/chat/getModelList | 模型列表 | 否 |
| POST | /service/chat/addModel | 新增模型 | 需 |
| PUT | /service/chat/updateModel | 更新模型 | 需 |
| DELETE | /service/chat/deleteModel/{modelId} | 删除模型（软删除） | 需 |
| WS | /service/chat/ws/chat | WebSocket 聊天 | 需（token 参数） |
| POST | /service/chat/uploadDoc/{tenantId}/{directoryId} | 上传文档 | 需 |
| GET | /service/chat/getDocListByDirId | 按目录查文档 | 需 |
| GET | /service/chat/getDocList | 按租户查文档 | 需 |
| DELETE | /service/chat/deleteDoc/{doc_id} | 删除文档 | 需 |
| GET | /service/chat/getDirectoryList | 目录列表 | 需 |
| POST | /service/chat/createDir | 创建目录 | 需 |
| PUT | /service/chat/renameDir | 重命名目录 | 需 |
| PUT | /service/chat/deleteDir/{directoryId} | 删除目录 | 需 |

## 接口详情

### 1. AI 对话（HTTP 流式）
- 接口：`POST /service/chat/chat`
- 作用：发起 AI 对话，流式返回文本（与 WebSocket 聊天逻辑一致）
- 入参：`X-User-Id`（Header）+ Body（ChatParamsEntity：`prompt`、`chatId`、`modelId`、`companyId`、`systemPrompt`、`docIds`、`showThink`、`type`、`language`、`tenantId`）
- 出参：流式文本（`text/plain;charset=utf-8`，非 ResultEntity）

### 2. 按会话查历史
- 接口：`GET /service/chat/getChatHistoryByChatId`
- 作用：根据会话 ID 查询该会话的聊天历史（按时间正序）
- 入参：`X-User-Id`（Header）+ Query：`chatId`
- 出参：ResultEntity，data 为该会话消息列表

### 3. 按租户查文档
- 接口：`GET /service/chat/getDocList`
- 作用：查询指定租户下的所有文档（含目录名称 directoryName）
- 入参：`X-User-Id`（Header）+ Query：`tenantId`
- 出参：ResultEntity，data 为文档列表

### 4. 重命名目录
- 接口：`PUT /service/chat/renameDir`
- 作用：重命名目录
- 入参：`X-User-Id`（Header）+ Body（RenameDirectorySchema：`id`、`directory`、`tenantId`）
- 出参：ResultEntity

### 5. 删除目录
- 接口：`PUT /service/chat/deleteDir/{directoryId}`
- 作用：删除指定目录
- 入参：`X-User-Id`（Header）+ Path：`directoryId`
- 出参：ResultEntity

### 1. 模型列表
- 接口：`GET /service/chat/getModelList`
- 入参（Query）：`companyId`（必填）、`keyword`（可选，按模型名模糊搜索）
- 出参：ResultEntity，data 为模型列表

### 2. 新增模型
- 接口：`POST /service/chat/addModel`
- 作用：添加模型（需企业管理员权限）
- 入参：`X-User-Id`（Header）+ Body（AddModelSchema）
- 出参：ResultEntity

### 3. 更新模型
- 接口：`PUT /service/chat/updateModel`
- 作用：更新模型（需企业管理员权限）
- 入参：`X-User-Id`（Header）+ Body（UpdateModelSchema）
- 出参：ResultEntity

### 4. 删除模型（软删除）
- 接口：`DELETE /service/chat/deleteModel/{modelId}`
- 入参：`X-User-Id`（Header）+ Query：`companyId` + Path：`modelId`
- 出参：ResultEntity

### 5. WebSocket 聊天
- 接口：`WS /service/chat/ws/chat`
- 作用：WebSocket 方式 AI 对话（流式）
- 入参：`?token=<token>`（网关注入 `X-User-Id`）；消息体通过 send 发送 JSON（prompt、chatId、modelId、docIds、showThink、type、language、companyId、tenantId 等）
- 出参：流式文本消息

### 6. 上传文档
- 接口：`POST /service/chat/uploadDoc/{tenantId}/{directoryId}`
- 入参：`X-User-Id`（Header）+ Path：`tenantId`、`directoryId` + Form：`file`（文件）
- 出参：ResultEntity

### 7. 删除文档
- 接口：`DELETE /service/chat/deleteDoc/{doc_id}`
- 入参：`X-User-Id`（Header）+ Path：`doc_id`
- 出参：ResultEntity

### 8. 分页聊天历史
- 接口：`GET /service/chat/getChatHistory`
- 入参：`X-User-Id`（Header）+ Query：`pageNum`、`pageSize`、`tenantId`（可选）
- 出参：ResultEntity，data 为历史列表，`total` 为总数

### 9. 按目录查文档
- 接口：`GET /service/chat/getDocListByDirId`
- 入参：`X-User-Id`（Header）+ Query：`directoryId`
- 出参：ResultEntity，data 为文档列表

### 10. 目录列表
- 接口：`GET /service/chat/getDirectoryList`
- 入参：`X-User-Id`（Header）+ Query：`tenantId`
- 出参：ResultEntity，data 为目录列表

### 11. 创建目录
- 接口：`POST /service/chat/createDir`
- 入参：`X-User-Id`（Header）+ Body（CreateDirectoryShema：`tenantId`、`directory`）
- 出参：ResultEntity

## 请求体实体字段

**AddModelSchema / UpdateModelSchema**（模型）

| 字段 | 类型 | 说明 |
|------|------|------|
| type | str | 大模型类型（ollama/deepseek/tongyi） |
| apiKey | str | 在线大模型 api_key |
| modelName | str | 模型名称 |
| baseUrl | str | API 基础路径 |
| disabled | int | 是否禁用（0 启用 / 1 禁用） |
| companyId | str | 所属公司 id |
