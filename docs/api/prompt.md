# prompt 提示词模块接口文档

> 服务名：prompt-service | 端口：4008 | 路径前缀：/service/prompt

## 概述

提示词模块：提示词的查询、新增、更新、删除、分页列表。

## 鉴权

所有接口均需 token（网关注入 `X-User-Id`）。

## 接口总览

| 方法 | 接口 | 作用 | 鉴权 |
|------|------|------|------|
| GET | /service/prompt/getPrompt | 查提示词 | 需 |
| GET | /service/prompt/getPromptList | 分页提示词列表 | 需 |
| POST | /service/prompt/insertPrompt | 新增提示词 | 需 |
| DELETE | /service/prompt/deletePrompt/{promptId} | 删除提示词 | 需 |
| PUT | /service/prompt/updatePrompt | 更新提示词 | 需 |

> 差异：Spring Boot 的 `deletePrompt/{tenantId}/{id}`（两个路径参数）改为 `deletePrompt/{promptId}`（tenantId 走 Query）；`insertPrompt` 由 PUT 改为 POST。

## 接口详情

### 1. 查提示词
- 接口：`GET /service/prompt/getPrompt`
- 作用：根据租户查默认提示词（无则自动创建），或按 id 精确查询单条
- 入参：`X-User-Id`（Header）+ Query：`tenantId`（必填）、`promptId`（可选）
- 出参：ResultEntity，data 为提示词

### 2. 分页提示词列表
- 接口：`GET /service/prompt/getPromptList`
- 入参：`X-User-Id`（Header）+ Query：`tenantId`、`keyword`（可选）、`pageNum`（默认 1）、`pageSize`（默认 10，最大 100）
- 出参：ResultEntity，data 为提示词列表，`total` 为总数

### 3. 新增提示词
- 接口：`POST /service/prompt/insertPrompt`
- 入参：`X-User-Id`（Header）+ Body（InsertPromptSchema）
- 出参：ResultEntity

### 4. 删除提示词
- 接口：`DELETE /service/prompt/deletePrompt/{promptId}`
- 入参：`X-User-Id`（Header）+ Path：`promptId` + Query：`tenantId`
- 出参：ResultEntity

### 5. 更新提示词
- 接口：`PUT /service/prompt/updatePrompt`
- 入参：`X-User-Id`（Header）+ Body（UpdatePromptSchema）
- 出参：ResultEntity

## 请求体实体字段

**InsertPromptSchema / UpdatePromptSchema**

| 字段 | 类型 | 说明 |
|------|------|------|
| tenantId | str | 租户 ID |
| prompt | str | 提示词内容/标题 |
