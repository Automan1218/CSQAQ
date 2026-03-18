# CSQAQ TODO

## 高优先级（Phase 3 前必做）

- [ ] **并行子图执行** — 用户查询单品时，同时并行拉取大盘上下文给 Advisor 参考
- [ ] **HITL 高风险确认** — risk_level=high 时中断等待用户确认再执行

## 中优先级（Phase 3）

- [ ] **K线技术分析增强** — Market Agent 接入指数K线图端点，增加MA/趋势判断
- [ ] **Scout 全维度扫描** — 扩展到租赁、挂刀套现、存世量等维度
- [ ] **记忆系统** — 对话历史持久化 + ChromaDB 向量检索
- [ ] **监控系统** — WatchlistMonitor + MarketMonitor 后台轮询

## 低优先级（Phase 4）

- [ ] **Server mode** — FastAPI + WebSocket 推送
- [ ] **多用户认证** — JWT token 管理
- [ ] **通知推送** — Webhook 告警
