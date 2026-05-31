# DCBOT

一个使用 `discord.py` 编写的 Discord 机器人项目，支持前缀命令、Slash Commands、模块化扩展和可选的 HTTP 管理 API。

仓库仅包含源码，不包含任何 token、密码、数据库、私有配置或运行数据。

## 功能

- 用户上线时发送私信问候
- `/math` 基础计算器
- 新成员验证流程
- 论坛推荐帖发布和编辑
- 基于 SQLite 的敏感词管理与自动检测
- 可选 AI 聊天模块
- 可选机器人离线邮件提醒
- FastAPI 管理 API，可列出命令和扩展模块

## 目录结构

```text
lla/
├─ python/
│  ├─ lla-example.py          机器人入口
│  ├─ presence_greeter.py     上线问候
│  ├─ math_commands.py        计算器
│  ├─ member_gate.py          新成员验证
│  ├─ work_recommend.py       推荐帖发布
│  ├─ recommend_edit.py       推荐帖编辑
│  ├─ sensitive_words.py      敏感词检测
│  ├─ ai_chat.py              可选 AI 聊天
│  └─ offline_email_alert.py  可选离线邮件提醒
└─ manager_api/
   ├─ app/                    FastAPI 管理 API
   └─ requirements.txt        管理 API 依赖
```

## 安装

建议使用 Python 虚拟环境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install discord.py python-dotenv
pip install -r .\lla\manager_api\requirements.txt
```

如果启用 AI 聊天模块，还需要安装对应的 OpenAI-compatible SDK：

```powershell
pip install openai
```

## 配置

在项目根目录创建本地配置目录：

```text
lla/config/
lla/data/
```

至少需要通过环境变量提供 Discord bot token：

```powershell
$env:LLA_BOT_TOKEN="your-discord-bot-token"
```

管理 API 默认随机器人启动，默认监听：

```text
http://127.0.0.1:8765
```

建议额外设置管理 API token：

```powershell
$env:DCBOT_ADMIN_TOKEN="your-random-admin-token"
```

不要把 `.env`、token、密码、数据库或私有 JSON 配置提交到仓库。

## 运行

从项目根目录执行：

```powershell
python .\lla\python\lla-example.py
```

首次启动前，请在 Discord Developer Portal 中为机器人开启：

```text
Message Content Intent
Presence Intent
Server Members Intent
```

## 同步命令

机器人上线后，拥有管理员权限的用户可以在服务器内执行：

```text
!syncCommand
```

该命令会把 Slash Commands 同步到当前 Discord 服务器。

## 管理 API

管理 API 也可以单独运行：

```powershell
cd .\lla\manager_api
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

接口包括：

```text
GET  /api/status
GET  /api/commands
GET  /api/extensions
POST /api/extensions/{name}/enable
POST /api/extensions/{name}/disable
```

## 安全提示

- 使用环境变量保存 token 和密码。
- 不要提交 `.env`、`*.json`、`*.db`、日志或备份包。
- 管理 API 不建议直接暴露到公网。
- 公网部署时，建议使用防火墙、反向代理和 HTTPS。
