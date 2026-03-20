# 存世量趋势分析（Inventory Trend Analysis）设计文档

## 概述

为 CSQAQ CS2 饰品投资分析系统新增存世量趋势分析能力。通过 90 天存世量走势数据，结合价格趋势和自然语言规则库，识别庄家行为（吸货、控盘、抛压等），为投资决策提供额外维度。

## 需求

### 功能需求

1. **单品查询增强**：用户查询单品时，自动并行拉取存世量趋势，分析结果纳入 Advisor 综合判断
2. **独立存世量查询**：新增 `inventory_query` intent，支持用户专门查询某饰品的存世量趋势
3. **可扩展规则库**：YAML 自然语言规则库，用户可自行增删规则，LLM 读取规则做业务解读
4. **存世量×价格交叉分析**：结合价格趋势与存世量趋势，识别组合模式（如"量减价稳=吸货"）

### 非功能需求

- 存世量分支与 market/scout 并行执行，不增加总延迟
- 规则库为 YAML 文件，CLI 模式每次运行自动加载，无需重启
- 分析模块为纯计算，无 LLM 依赖，易于测试

## 架构设计

### 整体流程

```
用户查询
  │
  ├─ item_query ──→ parallel_item_flow
  │                   ├─ item_branch (resolve → fetch_chart → analyze)
  │                   ├─ market_branch (并行)
  │                   ├─ scout_branch (并行)
  │                   └─ inventory_branch (依赖 good_id，与 market/scout 并行)
  │                   ↓
  │                 merge_contexts (item + market + scout + inventory)
  │                   ↓
  │                 advisor → END
  │
  ├─ inventory_query ──→ inventory_flow
  │                       resolve_item → fetch_inventory → analyze_inventory
  │                         → interpret_inventory → advisor → END
  │
  ├─ market_query ──→ (不变)
  └─ scout_query ──→ (不变)
```

### §1 数据层

**扩展 `ItemAPI`**，新增 `get_item_statistic(good_id: int)` 方法：

- 调用 `GET /api/v1/info/good/statistic?id={good_id}`
- 响应 schema 为 `InventoryStat`（statistic: int, created_at: str）
- API 返回 180 天数据，客户端按日期截取近 90 天（`created_at >= today - 90 days`），处理可能的缺失天数
- 截取逻辑放在 API 层，上层调用者无需关心原始数据范围

**与 `VolItem.statistic` 的关系**：`VolItem`（来自 `/info/vol_data_info`）的 `statistic` 字段是单时间点快照，用于排行榜场景。新的 `InventoryStat`（来自 `/info/good/statistic`）是 90 天时间序列，用于趋势分析。两者数据来源不同、用途不同，互不替代。

**新增文件**：`infrastructure/csqaq_client/inventory_schemas.py`

### §2 存世量分析模块

放在 `components/analysis/inventory_analyzer.py`，与现有 TA 模块同级。

**趋势分析**：
- 复用 `TechnicalIndicators` 的 MA、volatility、momentum 等计算方法
- 存世量本质是时间序列，共享相同数学工具
- 产出 `InventoryReport`（趋势方向、变化速率、波动率、信号列表）

**信号检测**：
- 新增存世量专属检测器（加速减少、突然大变、拐点等）
- 复用现有 `Signal` dataclass 框架，保持信号格式统一

**适用指标**：存世量时间序列适用 MA（趋势平滑）、volatility（波动率）、momentum（变化速率）。RSI、MACD、Bollinger Bands 等价格专用指标不适用于存世量数据，`inventory_analyzer` 应明确跳过这些。

**设计决策**：存世量分析模块只做"存世量自身的趋势判断"，不涉及价格。价格×存世量的交叉判断交给规则引擎（§3）。保持单一职责 — 分析模块是纯计算，规则引擎是业务判断。

### §3 规则引擎

**存储**：`src/csqaq/rules/inventory_rules.yaml`（新建 `rules/` 目录），自然语言规则。使用 `importlib.resources` 或 `pathlib` 相对路径加载，确保打包后仍可访问。

**规则格式**：每条规则包含名称和自然语言描述，描述中包含触发条件和业务含义。不做结构化条件匹配 — 由 LLM 结合分析数据理解和应用规则。

**示例规则**：

```yaml
rules:
  - name: 盘主吸货
    description: 存世量持续减少，价格稳定或微涨，可能有盘主在吸货，看多信号

  - name: 控盘风险
    description: 存世量持续减少且价格快速上涨，说明已被控盘，追高风险大

  - name: 抛压信号
    description: 存世量持续增加，价格下跌，市场抛压较重或开箱量大，看空

  - name: 异常扫货
    description: 存世量突然大幅减少，可能有大单扫货，需关注后续价格变动
```

**匹配流程**：Inventory Agent 的 interpret 节点将 YAML 规则全文注入 LLM system prompt，LLM 结合存世量分析结果 + 价格上下文，判断哪些规则适用并给出业务解读。

**扩展方式**：编辑 YAML 文件即可，CLI 模式每次运行重新加载。未来 Server mode 可加文件 watch 或 API 管理。

### §4 Inventory Agent

独立 agent，`components/agents/inventory.py`，三个节点：

1. **fetch_inventory_node** — 通过 `ItemAPI.get_item_statistic()` 拉取 90 天存世量数据
2. **analyze_inventory_node** — 调用 §2 分析模块，产出 `InventoryReport`
3. **interpret_inventory_node** — LLM 节点。System prompt 注入：
   - YAML 规则库内容
   - 存世量分析结果（趋势、速率、信号）
   - 价格上下文（来自 `item_context`，如果有的话）
   - 输出业务解读

输出为 `inventory_context`，传给 Advisor 作为第五个上下文来源（alongside item_context、market_context、scout_context、historical_advice）。

### §5 流程集成

**Router 扩展**：
- 新增 `inventory_query` intent，更新 `IntentResult` 验证集和 LLM prompt
- 关键词触发规则：包含"存世量"、"库存趋势"、"吸货"、"控盘"等关键词时路由到 `inventory_query`
- 意图区分：`item_query`（"分析 AK-47 红线"）在并行流中自动带上存世量分析；`inventory_query`（"AK-47 红线的存世量趋势"）走专用存世量流程
- Router LLM prompt 新增第四类意图描述

**parallel_item_flow 扩展**：
- 重构 `prepare_queries` 节点：在并行 fork 之前，调用 `item_api.search_suggest()` + `item_api.get_item_detail()` 完成饰品解析，将 `good_id` 和 `item_detail` 写入共享 state
- `ParallelItemFlowState` 新增字段：`good_id: int | None`、`item_detail: dict | None`、`inventory_context: dict | None`、`inventory_error: str | None`
- `_run_item_branch` 重构：不再调用 `resolve_item_node`，直接从 state 读取 `good_id` 和 `item_detail`，只负责 fetch_chart → analyze
- 新增第 4 并行分支 `_run_inventory_branch`，从 state 读取 `good_id`，与 item/market/scout 真正并行

**独立查询流程**：
- 新增 `flows/inventory_flow.py` 编排子图
- 流程：resolve_item → fetch_item_detail（获取价格数据供规则引擎使用）→ inventory agent 3 节点 → advisor → END
- 独立查询场景下 Advisor 仅收到 `inventory_context`（可能含价格快照），输出范围较窄，这是预期行为

**Advisor 扩展**：
- `advise_node` 的 context 构建逻辑新增 `inventory_context` 分支
- System prompt 新增存世量分析说明："inventory_context 包含存世量趋势分析和基于规则库的业务解读（庄家行为判断等），作为投资建议的参考维度之一"
- `inventory_context` 与其他三个 context 同等级别，Advisor 综合权衡

**错误处理**：
- `_run_inventory_branch` 遵循现有模式：异常捕获 → 存入 `inventory_error`，`inventory_context` 保持 None，Advisor 正常执行（缺失的 context 不影响其他维度的分析）

**merge_contexts**：
- 当前 `merge_contexts` 是 pass-through（state 通过 LangGraph 自动传播），新增 `inventory_context` 后保持此模式即可

## 文件变更清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `infrastructure/csqaq_client/inventory_schemas.py` | InventoryStat Pydantic schema |
| `components/analysis/inventory_analyzer.py` | 存世量趋势分析（复用 TechnicalIndicators） |
| `components/agents/inventory.py` | Inventory Agent（3 节点） |
| `flows/inventory_flow.py` | 独立存世量查询子图 |
| `rules/inventory_rules.yaml` | 自然语言规则库 |

### 修改文件

| 文件 | 变更内容 |
|------|----------|
| `infrastructure/csqaq_client/item.py` | 新增 `get_item_statistic` 方法 |
| `components/router.py` | 新增 `inventory_query` intent |
| `flows/parallel_item_flow.py` | 新增第 4 并行分支 |
| `flows/router_flow.py` | 新增 inventory_subflow 路由；更新 `_item_subflow_node` 初始 state dict 包含 `good_id`、`inventory_context`、`inventory_error` 等新字段 |
| `components/agents/advisor.py` | prompt 扩展支持 inventory_context |

## 领域知识

### CS2 饰品存世量解读

存世量（inventory/statistic）代表某饰品在市场中的总流通数量。变化来源：
- **减少**：被购买后进入 7 天交易冷却期（T+7）、被使用/消耗
- **增加**：开箱获得、冷却期结束重新上架
- **庄家行为**：大量买入导致存世量快速下降（吸货），控盘后拉升价格

### 初始规则集

| 模式 | 存世量趋势 | 价格趋势 | 含义 |
|------|-----------|---------|------|
| 盘主吸货 | 持续减少 | 稳定/微涨 | 看多信号 |
| 控盘风险 | 持续减少 | 快速上涨 | 追高风险大 |
| 抛压信号 | 持续增加 | 下跌 | 看空 |
| 异常扫货 | 突然大减 | — | 异常信号，需关注 |
