# CSQAQ TODO

## Phase 3（planned）

- [ ] **并行子图执行** — 用户查询单品时，同时并行拉取大盘上下文给 Advisor 参考
- [ ] **K线技术分析增强** — Market Agent 接入 sub/kline 接口，增加MA/趋势判断
- [ ] **Scout 全维度扫描** — 加入存世量、租赁价等更多排行维度
- [ ] **记忆系统** — 对话历史持久化 + ChromaDB 向量存储
- [ ] **HITL 高风险确认** — risk_level=high 时中断等待用户确认

## Phase 4（planned）

- [ ] **Server mode** — FastAPI + WebSocket 推送
- [ ] **监控 Agent** — 价格/库存变动告警
- [ ] **存世量趋势分析** — 利用单品存世量走势接口
