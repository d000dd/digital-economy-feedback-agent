# 测试报告

## 测试命令

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

## 覆盖范围

| 测试文件 | 覆盖内容 |
| --- | --- |
| `tests/test_agent.py` | 完整分析流程、空输入、CSV 中文字段、AI 失败回退 |
| `tests/test_llm.py` | `OPENAI_API_KEY` 自动启用真实 AI、强制离线规则、`.env` 兜底且不覆盖系统环境变量 |
| `tests/test_nlp.py` | 主题分类、情绪识别、优先级判断 |
| `tests/test_feishu.py` | 飞书签名、卡片结构、缺少 Webhook 的异常处理 |

## 迭代策略

1. 先保证无外部依赖的离线可运行版本；
2. 再加入飞书推送、真实 AI 接入和跨设备部署；
3. 每次修改核心逻辑后运行单元测试；
4. 用示例 CSV 生成 Markdown 和 JSON，检查报告结构。

## 当前结论

当前执行结果：

```text
Ran 13 tests in 0.016s
OK
```

CLI 端到端命令已生成 `outputs/report.md` 和 `outputs/result.json`。Web 服务已通过 `/api/health`、`/api/config`、`/api/analyze` 和首页 HTML 请求验证。即使没有 API key 或飞书配置，也能完成数据分析、报告生成和 Web 展示。
