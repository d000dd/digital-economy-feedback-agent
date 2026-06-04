# 飞书连接说明

## 创建机器人

1. 在飞书群聊中添加“自定义机器人”。
2. 复制 Webhook URL。
3. 如开启“签名校验”，复制签名密钥。
4. 在命令行或 Web 界面中填写配置。

## 命令行推送

```bash
export FEISHU_WEBHOOK_URL="https://open.feishu.cn/open-apis/bot/v2/hook/xxxx"
export FEISHU_WEBHOOK_SECRET="可选签名密钥"
PYTHONPATH=src python3 -m feedback_agent analyze -i data/sample_feedback.csv --push-feishu
```

## Web 界面推送

启动服务：

```bash
PYTHONPATH=src python3 -m feedback_agent serve --port 8765
```

在页面完成分析后，填写 Webhook URL 和签名密钥，点击“推送飞书”。

## 与 nanobot 的关系

nanobot 中已经有完整飞书 channel。这个作业项目复用了其中的工程思路，而不是复制整套框架：

- 将卡片格式构造和 HTTP 发送分离；
- 对签名密钥做 HMAC-SHA256 签名；
- 发送失败时重试；
- 用结构化卡片承载摘要、主题分布和建议动作。

这样项目更小，适合作业提交和现场演示。
