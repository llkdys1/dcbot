# DCBOT

[中文](#中文) | [English](#english) | [日本語](#日本語)

## 中文

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

---

## English

A Discord bot project built with `discord.py`. It supports prefix commands, Slash Commands, modular extensions, and an optional HTTP management API.

This repository contains source code only. It does not include tokens, passwords, databases, private configuration files, or runtime data.

### Features

- Send direct-message greetings when configured users come online
- `/math` basic calculator
- New member verification flow
- Forum recommendation post creation and editing
- SQLite-backed sensitive-word management and automatic moderation
- Optional AI chat module
- Optional email alerts when the bot disconnects
- FastAPI management API for listing commands and extensions

### Project Structure

```text
lla/
├─ python/
│  ├─ lla-example.py          Bot entry point
│  ├─ presence_greeter.py     Online greetings
│  ├─ math_commands.py        Calculator
│  ├─ member_gate.py          Member verification
│  ├─ work_recommend.py       Recommendation post creation
│  ├─ recommend_edit.py       Recommendation post editing
│  ├─ sensitive_words.py      Sensitive-word moderation
│  ├─ ai_chat.py              Optional AI chat
│  └─ offline_email_alert.py  Optional disconnect email alerts
└─ manager_api/
   ├─ app/                    FastAPI management API
   └─ requirements.txt        Management API dependencies
```

### Installation

Using a Python virtual environment is recommended:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install discord.py python-dotenv
pip install -r .\lla\manager_api\requirements.txt
```

If you enable the AI chat module, install an OpenAI-compatible SDK:

```powershell
pip install openai
```

### Configuration

Create local configuration directories in the project root:

```text
lla/config/
lla/data/
```

At minimum, provide the Discord bot token through an environment variable:

```powershell
$env:LLA_BOT_TOKEN="your-discord-bot-token"
```

The management API starts with the bot by default and listens on:

```text
http://127.0.0.1:8765
```

It is recommended to set an additional management API token:

```powershell
$env:DCBOT_ADMIN_TOKEN="your-random-admin-token"
```

Do not commit `.env` files, tokens, passwords, databases, or private JSON configuration files.

### Running The Bot

Run this command from the project root:

```powershell
python .\lla\python\lla-example.py
```

Before the first launch, enable the following options for the bot in the Discord Developer Portal:

```text
Message Content Intent
Presence Intent
Server Members Intent
```

### Synchronizing Commands

After the bot comes online, a user with administrator permission can run:

```text
!syncCommand
```

This command synchronizes the Slash Commands to the current Discord server.

### Management API

The management API can also run independently:

```powershell
cd .\lla\manager_api
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

Available endpoints:

```text
GET  /api/status
GET  /api/commands
GET  /api/extensions
POST /api/extensions/{name}/enable
POST /api/extensions/{name}/disable
```

### Security Notes

- Store tokens and passwords in environment variables.
- Do not commit `.env`, `*.json`, `*.db`, log, or backup files.
- Do not expose the management API directly to the public internet.
- For public deployments, use a firewall, reverse proxy, and HTTPS.

---

## 日本語

`discord.py` を使用して開発された Discord Bot プロジェクトです。プレフィックスコマンド、Slash Commands、モジュール形式の拡張機能、任意で利用できる HTTP 管理 API に対応しています。

このリポジトリにはソースコードのみが含まれています。トークン、パスワード、データベース、非公開設定、実行時データは含まれていません。

### 機能

- 設定したユーザーがオンラインになった際に DM で挨拶を送信
- `/math` 基本計算機
- 新規メンバーの認証フロー
- フォーラム向けおすすめ投稿の作成と編集
- SQLite を使用した禁止ワード管理と自動モデレーション
- 任意で利用できる AI チャットモジュール
- Bot 切断時の任意メール通知
- コマンドと拡張機能を一覧表示する FastAPI 管理 API

### ディレクトリ構成

```text
lla/
├─ python/
│  ├─ lla-example.py          Bot のエントリーポイント
│  ├─ presence_greeter.py     オンライン時の挨拶
│  ├─ math_commands.py        計算機
│  ├─ member_gate.py          メンバー認証
│  ├─ work_recommend.py       おすすめ投稿の作成
│  ├─ recommend_edit.py       おすすめ投稿の編集
│  ├─ sensitive_words.py      禁止ワードの検出
│  ├─ ai_chat.py              任意 AI チャット
│  └─ offline_email_alert.py  任意の切断メール通知
└─ manager_api/
   ├─ app/                    FastAPI 管理 API
   └─ requirements.txt        管理 API の依存パッケージ
```

### インストール

Python の仮想環境を使用することを推奨します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install discord.py python-dotenv
pip install -r .\lla\manager_api\requirements.txt
```

AI チャットモジュールを有効にする場合は、OpenAI 互換 SDK もインストールしてください。

```powershell
pip install openai
```

### 設定

プロジェクトのルートディレクトリにローカル設定用ディレクトリを作成します。

```text
lla/config/
lla/data/
```

最低限、Discord Bot のトークンを環境変数で設定してください。

```powershell
$env:LLA_BOT_TOKEN="your-discord-bot-token"
```

管理 API は初期設定では Bot と同時に起動し、次のアドレスで待機します。

```text
http://127.0.0.1:8765
```

管理 API 用のトークンも設定することを推奨します。

```powershell
$env:DCBOT_ADMIN_TOKEN="your-random-admin-token"
```

`.env`、トークン、パスワード、データベース、非公開 JSON 設定はリポジトリにコミットしないでください。

### 実行

プロジェクトのルートディレクトリで次のコマンドを実行します。

```powershell
python .\lla\python\lla-example.py
```

初回起動前に、Discord Developer Portal で次の設定を有効にしてください。

```text
Message Content Intent
Presence Intent
Server Members Intent
```

### コマンドの同期

Bot の起動後、管理者権限を持つユーザーはサーバー内で次のコマンドを実行できます。

```text
!syncCommand
```

このコマンドは Slash Commands を現在の Discord サーバーに同期します。

### 管理 API

管理 API は単独でも起動できます。

```powershell
cd .\lla\manager_api
uvicorn app.main:app --host 127.0.0.1 --port 8765 --reload
```

利用可能なエンドポイント：

```text
GET  /api/status
GET  /api/commands
GET  /api/extensions
POST /api/extensions/{name}/enable
POST /api/extensions/{name}/disable
```

### セキュリティ上の注意

- トークンとパスワードは環境変数に保存してください。
- `.env`、`*.json`、`*.db`、ログ、バックアップファイルをコミットしないでください。
- 管理 API を直接インターネットに公開しないでください。
- 公開環境では、ファイアウォール、リバースプロキシ、HTTPS を使用してください。
