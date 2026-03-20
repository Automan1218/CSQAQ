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
- **解决**: 用户手动导出 API 文档到 `docs/CSQAQ_Api/`，据此编写 Schema
- **状态**: 已解决

### 5. 成交量接口标注"暂停更新"但仍可访问
- **问题**: VolAPI 对应的 `/info/vol_data_info` 端点文档标注暂停更新
- **解决**: 先使用，后续确认数据时效性

### 6. 存世量只有单品接口，无排行榜
- **问题**: 存世量数据只能按单品查询，不支持批量排行
- **解决**: 已解决：排行榜 filter 支持 `存世量_存世量_升序/降序`

### 7. 排行榜 filter 参数完整列表在外部文档
- **问题**: rank_list 的 filter body 支持多种排序维度，但完整列表只在外部文档
- **解决**: 已解决：Phase 3 实现全维度扫描，RANK_FILTERS 包含7个排序维度
