# CSQAQ 遇到的困难与解决方案

## Phase 1

### 1. Apifox / docs.csqaq.com 文档无法爬取
- **问题**: CSQAQ API 文档托管在 Apifox 和 docs.csqaq.com，均使用 Remix 框架客户端渲染，WebFetch 只能获取初始化脚本
- **解决**: 用户手动将 API 索引导出到 `docs/CSQAQ_Api/api.txt`，开发时参考已有 client 代码模式推断 API 格式
- **后续**: 如需精确字段，用户从 Apifox 导出 OpenAPI JSON

### 2. LangGraph 节点函数依赖注入
- **问题**: LangGraph 节点签名必须是 `(state) -> dict`，无法直接传入 API client 等依赖
- **解决**: 使用 `functools.partial` 预绑定依赖参数

### 3. volume_trend 对称窗口数据不足
- **问题**: 改为对称窗口对比后，测试数据不够 `window * 2` 长度导致测试失败
- **解决**: 测试数据从 5 个元素增加到 6 个（window=3 需要 6 个）

## Phase 2

### 4. Market/Rank API 端点路径和响应格式未知
- **问题**: 与 Phase 1 同理，API 文档无法爬取。Phase 2 新增 4 个端点（MarketAPI 2个 + RankAPI 2个），路径和响应字段均未确认
- **解决**: 实现时第一步用真实 API token 探测端点，通过实际响应确认路径、字段名、数据类型，再编写 Schema
- **状态**: 待实施

（开发过程中继续补充）
