# music 音乐模块接口文档

> 服务名：music-service | 端口：4002 | 路径前缀：/service/music

## 概述

音乐模块：关键词推荐、分类、列表、歌手、收藏歌手、播放记录、点赞、搜索、歌手分类、收藏夹。

## 鉴权

除 `getMusicClassify`、`getMusicAuthorCategory` 外，其余接口均需 token（网关注入 `X-User-Id`）。

## 接口总览

| 方法 | 接口 | 作用 | 鉴权 |
|------|------|------|------|
| GET | /service/music/getKeywordMusic | 搜索框推荐音乐（热门） | 需 |
| GET | /service/music/getMusicClassify | 音乐分类 | 否 |
| GET | /service/music/getMusicListByClassifyId | 按分类取音乐列表 | 需 |
| GET | /service/music/getMusicAuthorListByCategoryId | 按分类取歌手 | 需 |
| GET | /service/music/getMusicListByAuthorId | 按歌手取音乐 | 需 |
| GET | /service/music/getFavoriteAuthor | 收藏的歌手 | 需 |
| POST | /service/music/insertFavoriteAuthor/{authorId} | 收藏歌手 | 需 |
| DELETE | /service/music/deleteFavoriteAuthor/{authorId} | 取消收藏歌手 | 需 |
| GET | /service/music/getMusicRecord | 播放记录 | 需 |
| POST | /service/music/insertMusicRecord | 插入播放记录 | 需 |
| POST | /service/music/insertMusicLike/{id} | 点赞音乐 | 需 |
| DELETE | /service/music/deleteMusicLike/{id} | 取消点赞音乐 | 需 |
| GET | /service/music/getMusicLike | 点赞的音乐 | 需 |
| GET | /service/music/searchMusic | 搜索音乐 | 需 |
| GET | /service/music/queryMusic | 多条件查询音乐 | 需 |
| GET | /service/music/getMusicAuthorCategory | 歌手分类 | 否 |
| GET | /service/music/getFavoriteDirectory | 收藏夹列表 | 需 |
| POST | /service/music/insertFavoriteDirectory | 创建收藏夹 | 需 |
| DELETE | /service/music/deleteFavoriteDirectory/{directoryId} | 删除收藏夹 | 需 |
| GET | /service/music/getMusicListByFavoriteId | 收藏夹音乐 | 需 |
| PUT | /service/music/updateFavoriteDirectory | 更新收藏夹名称 | 需 |
| GET | /service/music/isMusicFavorite/{musicId} | 是否已收藏 | 需 |
| POST | /service/music/insertMusicFavorite/{musicId} | 添加到收藏夹 | 需 |

> 差异（与 Spring Boot）：`deleteFavoriteDirectory/{favoriteId}` → `{directoryId}`；`getMusicListByAuthorId` 去掉 `authorName`；`getFavoriteAuthor` 去掉分页；`getMusicListByClassifyId` 去掉 `isRedis`；`insertMusicFavorite` body 为 `favoriteIds` int 数组。

## 接口详情

### 1. 搜索框推荐音乐
- 接口：`GET /service/music/getKeywordMusic`
- 作用：按 is_hot 降序取第一条音乐，用于搜索框推荐，含当前用户点赞状态
- 入参：`X-User-Id`（Header）
- 出参：ResultEntity，data 为单首音乐（含 isLike）

### 2. 音乐分类
- 接口：`GET /service/music/getMusicClassify`
- 入参：无
- 出参：ResultEntity，data 为分类列表

### 3. 按分类取音乐列表
- 接口：`GET /service/music/getMusicListByClassifyId`
- 入参：`X-User-Id`（Header）+ Query：`classifyId`、`pageNum`（默认 1）、`pageSize`（默认 10）
- 出参：ResultEntity，data 为音乐列表（含 isLike），`total` 为总数

### 4. 按分类取歌手
- 接口：`GET /service/music/getMusicAuthorListByCategoryId`
- 入参：`X-User-Id`（Header）+ Query：`categoryId`、`pageNum`、`pageSize`
- 出参：ResultEntity，data 为歌手列表

### 5. 按歌手取音乐
- 接口：`GET /service/music/getMusicListByAuthorId`
- 入参：`X-User-Id`（Header）+ Query：`authorId`、`pageNum`、`pageSize`
- 出参：ResultEntity，data 为音乐列表

### 6. 收藏的歌手
- 接口：`GET /service/music/getFavoriteAuthor`
- 作用：返回当前用户收藏的所有歌手（不分页）
- 入参：`X-User-Id`（Header）
- 出参：ResultEntity，data 为歌手列表

### 7. 收藏歌手
- 接口：`POST /service/music/insertFavoriteAuthor/{authorId}`
- 入参：`X-User-Id`（Header）+ Path：`authorId`
- 出参：ResultEntity，data=1（成功）

### 8. 取消收藏歌手
- 接口：`DELETE /service/music/deleteFavoriteAuthor/{authorId}`
- 入参：`X-User-Id`（Header）+ Path：`authorId`
- 出参：ResultEntity

### 9. 播放记录
- 接口：`GET /service/music/getMusicRecord`
- 入参：`X-User-Id`（Header）+ Query：`startDate`（可选）、`endDate`（可选）、`pageNum`（默认 1）、`pageSize`（默认 20）
- 出参：ResultEntity，data 为记录列表（含 times 播放次数）

### 10. 插入播放记录
- 接口：`POST /service/music/insertMusicRecord`
- 入参：`X-User-Id`（Header）+ Body（InsertMusicRecordSchema：`musicId`、`platform`、`version`、`device`）
- 出参：ResultEntity，data 为新增记录 ID

### 11. 点赞音乐
- 接口：`POST /service/music/insertMusicLike/{id}`
- 入参：`X-User-Id`（Header）+ Path：`id`（音乐 ID）
- 出参：ResultEntity

### 12. 取消点赞音乐
- 接口：`DELETE /service/music/deleteMusicLike/{id}`
- 入参：`X-User-Id`（Header）+ Path：`id`
- 出参：ResultEntity

### 13. 点赞的音乐
- 接口：`GET /service/music/getMusicLike`
- 入参：`X-User-Id`（Header）+ Query：`pageNum`（默认 1）、`pageSize`（默认 20）
- 出参：ResultEntity，data 为音乐列表

### 14. 搜索音乐
- 接口：`GET /service/music/searchMusic`
- 入参：`X-User-Id`（Header）+ Query：`keyword`、`pageNum`、`pageSize`
- 出参：ResultEntity，data 为音乐列表（含 isFavorite）

### 15. 多条件查询音乐
- 接口：`GET /service/music/queryMusic`
- 入参：`X-User-Id`（Header）+ Query（均可选）：`songName`、`authorName`、`albumName`、`language`、`publishStart`、`label` + `pageNum`、`pageSize`
- 出参：ResultEntity，data 为音乐列表（含 isFavorite），`total` 为总数

### 16. 歌手分类
- 接口：`GET /service/music/getMusicAuthorCategory`
- 入参：无
- 出参：ResultEntity，data 为歌手分类列表

### 17. 收藏夹列表
- 接口：`GET /service/music/getFavoriteDirectory`
- 入参：`X-User-Id`（Header）+ Query：`musicId`
- 出参：ResultEntity，data 为收藏夹列表（含 total、checked、cover）

### 18. 创建收藏夹
- 接口：`POST /service/music/insertFavoriteDirectory`
- 入参：`X-User-Id`（Header）+ Body（FavoriteDirectoryCreateSchema：`name`）
- 出参：ResultEntity，data 为创建的收藏夹

### 19. 删除收藏夹
- 接口：`DELETE /service/music/deleteFavoriteDirectory/{directoryId}`
- 入参：`X-User-Id`（Header）+ Path：`directoryId`
- 出参：ResultEntity

### 20. 收藏夹音乐
- 接口：`GET /service/music/getMusicListByFavoriteId`
- 入参：`X-User-Id`（Header）+ Query：`favoriteId`、`pageNum`、`pageSize`
- 出参：ResultEntity，data 为音乐列表（含 isLike）

### 21. 更新收藏夹名称
- 接口：`PUT /service/music/updateFavoriteDirectory`
- 入参：`X-User-Id`（Header）+ Body（FavoriteDirectoryUpdateSchema：`id`、`name`）
- 出参：ResultEntity，data 为受影响行数（1 成功 / 0 失败）

### 22. 是否已收藏
- 接口：`GET /service/music/isMusicFavorite/{musicId}`
- 入参：`X-User-Id`（Header）+ Path：`musicId`
- 出参：ResultEntity，data 为收藏数量（>0 表示已收藏）

### 23. 添加到收藏夹
- 接口：`POST /service/music/insertMusicFavorite/{musicId}`
- 作用：先删除该音乐所有收藏，再批量插入（传空数组则清空收藏）
- 入参：`X-User-Id`（Header）+ Path：`musicId` + Body：`favoriteIds`（int 数组，收藏夹 ID 列表）
- 出参：ResultEntity，data 为新增收藏记录数

## 请求体实体字段

**InsertMusicRecordSchema**

| 字段 | 类型 | 说明 |
|------|------|------|
| musicId | int | 音乐 id |
| platform | str | 平台 |
| device | str | 设备 |
| version | str | app 版本 |

**FavoriteDirectoryCreateSchema**：`name`（收藏夹名称）

**FavoriteDirectoryUpdateSchema**：`id`（收藏夹 ID）、`name`（新名称）
