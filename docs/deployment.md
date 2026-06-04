# 部署说明

本项目不依赖本机绝对路径。只要有 Python 3.11+，即可在另一台电脑、局域网服务器、Docker 或云平台运行。

## 环境变量

推荐直接使用 shell / 系统环境变量。只要变量已经 export，项目会直接读取，不需要创建 `.env`：

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4.1-mini"
```

如果当前目录存在 `.env`，CLI 会把它作为兜底配置读取；`.env` 只补充当前 shell 中缺失的变量，不会覆盖 bashrc/zshrc、Docker 或云平台里已经注入的环境变量。

关键变量：

| 变量 | 说明 |
| --- | --- |
| `HOST` | 服务监听地址。跨设备访问用 `0.0.0.0` |
| `PORT` | 服务端口，云平台通常自动注入 |
| `OPENAI_BASE_URL` | OpenAI 兼容接口地址，通常包含 `/v1` |
| `OPENAI_API_KEY` | 真实 AI 调用密钥 |
| `OPENAI_MODEL` | 模型名，例如 `gpt-4.1-mini` 或你的兼容服务模型 |
| `FEEDBACK_AGENT_USE_LLM` | `auto` 自动启用；`0` 强制离线规则 |
| `FEISHU_WEBHOOK_URL` | 飞书自定义机器人地址 |
| `FEISHU_WEBHOOK_SECRET` | 飞书签名密钥，可空 |

## 局域网部署

在主机上启动：

```bash
PYTHONPATH=src HOST=0.0.0.0 PORT=8765 python3 -m feedback_agent serve
```

同一 Wi-Fi 下的其他设备访问：

```text
http://<主机局域网IP>:8765
```

如果无法访问，检查系统防火墙是否允许 Python 监听该端口。

## 接入真实 AI

只要设置 `OPENAI_API_KEY`，后端会自动使用真实 AI 润色分析摘要；调用失败会回退到离线规则。

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_API_KEY="sk-..."
export OPENAI_MODEL="gpt-4.1-mini"
PYTHONPATH=src python3 -m feedback_agent serve
```

前端右上角会显示 `Live AI · <model>`。未配置密钥时显示 `Rules fallback`。

## Docker 部署

构建镜像：

```bash
docker build -t digital-economy-feedback-agent .
```

运行：

```bash
docker run --rm -p 8765:8765 \
  -e OPENAI_BASE_URL="https://api.openai.com/v1" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e OPENAI_MODEL="gpt-4.1-mini" \
  digital-economy-feedback-agent
```

访问：

```text
http://localhost:8765
```

局域网其他设备访问 `http://<主机IP>:8765`。

## 云平台部署

适合 Railway、Render、Fly.io、Heroku 类平台。

通用启动命令：

```bash
PYTHONPATH=src python -m feedback_agent serve --host 0.0.0.0 --port $PORT
```

需要配置的环境变量：

```text
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=<your-key>
OPENAI_MODEL=gpt-4.1-mini
FEISHU_WEBHOOK_URL=<optional>
FEISHU_WEBHOOK_SECRET=<optional>
```

注意：本项目没有登录鉴权。若部署到公网，建议放在有访问控制的平台、内网环境，或在反向代理层增加 Basic Auth / SSO，避免他人消耗你的 AI 额度。
