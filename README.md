__FastAPI 应用服务__

基于 FastAPI 构建的多功能应用服务，集成了用户管理和 AI 聊天功能，提供完整的用户认证、账户管理以及智能对话交互能力。

__项目概述__

本项目是一个模块化的 FastAPI 应用服务，包含两个核心模块：

  


- 用户服务（User Service）：提供用户认证、账户管理等基础功能
- 聊天服务（Chat Service）：提供 AI 对话、文档查询（RAG）等智能交互功能

__功能特性__

__用户服务（User Service）__

- __用户认证__
	- JWT 令牌认证
	- 用户名 / 密码登录
	- 邮箱验证码登录
- __账户安全__
	- 密码加密存储
	- 密码修改与重置
	- 邮箱验证流程
- __用户管理__
	- 用户注册
	- 个人信息更新
	- 头像上传
- __安全防护__
	- 请求认证中间件
	- 敏感操作验证
	- 账户禁用机制

__聊天服务（Chat Service）__

- __AI 对话__
	- 多模型支持（deepseek\-r1:8b、qwen3:8b 等）
	- WebSocket 实时通信
	- 思考过程展示（可切换）
- __文档管理__
	- 文档上传（PDF、TXT 等格式）
	- 文档删除
	- 文档列表查询
- __RAG 功能__
	- 基于文档的智能问答
	- 相关内容精准定位
	- 多文档联合查询
- __会话管理__
	- 聊天记录保存
	- 历史会话查询
	- 分页获取记录

__技术栈__

- 🐍 Python 3\.10\+
- ⚡ FastAPI 高性能框架
- 🛢️ SQLAlchemy 2\.0 ORM
- 🗃️ MySQL 数据库
- 🔑 JWT 认证
- 📧 SMTP 邮件服务
- 🧩 Redis 缓存服务
- 🔍 Elasticsearch 搜索引擎
- 🦜️🔗 LangChain 大模型应用框架
- 🦙 Ollama 本地大模型部署工具

__快速开始__

__环境准备__

1. 安装 Python 3\.10\+
2. 安装 Poetry 包管理工具
3. 准备 PostgreSQL 数据库
4. 准备 Redis 服务
5. 准备 Elasticsearch 服务
6. 部署 Ollama 及所需模型

__安装步骤__

1. 克隆仓库

bash

git clone https://github\.com/wuyuanwuhui999/fast\-api\-app\-service\.git

cd fast\-api\-app\-service

  


1. 创建虚拟环境

bash

python \-m venv env

  


1. 激活虚拟环境

bash

\# Windows

env\\Scripts\\activate

\# Linux/MacOS

source env/bin/activate

  


1. 安装依赖

bash

pip install \-r requirements\.txt

__运行服务__

1. 启动用户服务

bash

uvicorn user\.main:app \-\-reload \-\-port 8000

  


1. 启动聊天服务

bash

uvicorn chat\.main:app \-\-reload \-\-port 8001

__API 接口__

__用户服务接口__

- POST /service/user/register \- 用户注册
- POST /service/user/login \- 用户登录
- GET /service/user\-getway/getUserData \- 获取用户信息
- PUT /service/user\-getway/updateUser \- 更新用户信息
- PUT /service/user\-getway/updatePassword \- 修改密码
- POST /service/user/sendEmailVertifyCode \- 发送邮箱验证码
- POST /service/user\-getway/resetPassword \- 重置密码
- POST /service/user/loginByEmail \- 邮箱登录

__聊天服务接口__

- GET /service/ai/getModelList \- 获取模型列表
- WebSocket /service/ai/ws/chat \- 实时聊天接口
- POST /service/ai/uploadDoc \- 上传文档
- DELETE /service/ai/deleteDoc/\{doc\_id\} \- 删除文档
- GET /service/ai/getChatHistory \- 获取聊天历史
- GET /service/ai/getDocList \- 获取文档列表

__界面预览__

__项目结构__

项目采用模块化设计，主要目录结构如下：

  


- user/ \- 用户服务模块
	- routers/ \- 路由定义
	- services/ \- 业务逻辑
	- repositories/ \- 数据访问
	- models/ \- 数据模型
	- schemas/ \- 数据验证
- chat/ \- 聊天服务模块
	- routers/ \- 路由定义
	- services/ \- 业务逻辑
	- repositories/ \- 数据访问
	- models/ \- 数据模型
	- schemas/ \- 数据验证
	- utils/ \- 工具函数
- common/ \- 公共模块
	- config/ \- 配置文件
	- dependencies/ \- 依赖注入
	- models/ \- 公共模型
	- utils/ \- 公共工具

 

================================APP界面预览================================   
![ai智能聊天助手](ai智能聊天助手.png)
![ai聊天RAG文档查询](ai聊天RAG文档查询.png)
![ai聊天菜单功能](ai聊天菜单功能.png)
![ai聊天会话记录](ai聊天会话记录.png)
![ai聊天切换模型](ai聊天切换模型.png)
![ai聊天我的文档](ai聊天我的文档.png)
================================APP界面预览================================  
