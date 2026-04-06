# Growth OS — 函数参考文档

> 自动生成日期：2026-04-04
> 覆盖范围：`core/` · `phase1_product_discovery/` · `phase2_influencer/`

---

## 目录

- [core — 基础设施层](#core--基础设施层)
  - [config.py](#coreconfigpy)
  - [logger.py](#coreloggerpy)
  - [database.py](#coredatabasepy)
  - [base_agent.py](#corebase_agentpy)
  - [redis_client.py](#coreredis_clientpy)
  - [scheduler.py](#coreschedulerpy)
- [phase1 — 选品发现](#phase1--选品发现)
  - [crawlers/tiktok_crawler.py](#phase1crawlerstiktok_crawlerpy)
  - [crawlers/amazon_crawler.py](#phase1crawlersamazon_crawlerpy)
  - [crawlers/shopee_crawler.py](#phase1crawlersshopee_crawlerpy)
  - [crawlers/google_trends_crawler.py](#phase1crawlersgoogle_trends_crawlerpy)
  - [analyzers/product_scorer.py](#phase1analyzersproduct_scorerpy)
  - [agents/discovery_agent.py](#phase1agentsdiscovery_agentpy)
  - [scheduler_jobs.py](#phase1scheduler_jobspy)
  - [api.py](#phase1apipy)
- [phase2 — 达人招募](#phase2--达人招募)
  - [crawlers/influencer_crawler.py](#phase2crawlersinfluencer_crawlerpy)
  - [analyzers/influencer_scorer.py](#phase2analyzersinfluencer_scorerpy)
  - [agents/influencer_agent.py](#phase2agentsinfluencer_agentpy)
  - [scheduler_jobs.py](#phase2scheduler_jobspy)
  - [api.py](#phase2apipy)
- [main.py](#mainpy)

---

## core — 基础设施层

---

### `core/config.py`

全局配置管理，从 `.env` 读取环境变量，统一通过 `settings` 单例访问。

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_env(key: str, default: str = "") → str` | `str` | 读取环境变量，缺失时返回默认值 |

#### 数据类

| 数据类 | 关键字段 | 说明 |
|--------|----------|------|
| `DBConfig` | `url`, `pool_size=10`, `max_overflow=20`, `pool_recycle=3600` | MySQL 连接配置 |
| `RedisConfig` | `url`, `max_connections=20` | Redis 配置 |
| `AnthropicConfig` | `api_key`, `model="claude-sonnet-4-20250514"`, `max_tokens=4096` | Claude API 配置 |
| `TikTokConfig` | `app_key`, `app_secret`, `access_token`, `shop_id` | TikTok Open API 凭证 |
| `ShopeeConfig` | `partner_id`, `partner_key`, `access_token`, `shop_id` | Shopee Open Platform 凭证 |
| `AmazonConfig` | `access_key` | Amazon / Rainforest API 凭证 |
| `EmailConfig` | `smtp_host="smtp.gmail.com"`, `smtp_port=587`, `username`, `password`, `sender` | SMTP 邮件配置 |
| `WhatsAppConfig` | `phone_number_id`, `access_token` | WhatsApp Business API 配置 |
| `Settings` | `db`, `redis`, `anthropic`, `tiktok`, `shopee`, `amazon`, `email`, `whatsapp`, `mock_mode=True`, `debug=False` | 全局配置聚合单例 |

#### 全局实例

```python
settings = Settings()   # 全局唯一，所有模块通过此实例读取配置
```

---

### `core/logger.py`

统一日志配置，输出到 stdout。

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_make_logger() → logging.Logger` | `Logger` | 创建名为 `"growth_os"` 的 Logger，Level=INFO，格式含时间/级别/模块名 |

#### 全局实例

```python
logger   # 所有模块导入此实例记录日志
```

**日志格式：**
```
2026-04-04 02:00:00,123 [INFO] growth_os — [Scheduler] TikTok 抓取完成: 100 商品 | 1243ms
```

---

### `core/database.py`

异步 MySQL 连接池（SQLAlchemy 2.x + aiomysql），封装 CRUD 操作，启动时自动建表。

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `async init_db() → None` | `None` | 初始化连接池、Session 工厂，执行建表 DDL |
| `async close_db() → None` | `None` | 释放连接池资源 |
| `async get_db() → AsyncGenerator[AsyncSession, None]` | `AsyncSession` (context manager) | 获取 DB Session；自动提交/回滚 |
| `async execute(sql: str, params: dict = None) → None` | `None` | 执行参数化 SQL，不返回数据（INSERT/UPDATE/DELETE） |
| `async fetchall(sql: str, params: dict = None) → list[dict]` | `list[dict]` | 执行查询，返回全部行（列名为 key） |
| `async fetchone(sql: str, params: dict = None) → dict \| None` | `dict \| None` | 返回第一行，无结果返回 `None` |
| `async _create_all_tables() → None` | `None` | 私有：执行 `_DDL_STATEMENTS` 中所有建表语句 |

#### 数据库表

| 表名 | 所属 Phase | 关键字段 | 说明 |
|------|-----------|----------|------|
| `discovered_products` | Phase 1 | `platform`, `product_id`, `ai_score`, `ai_analysis` | AI 评分商品 |
| `trending_keywords` | Phase 1 | `keyword`, `platform`, `volume`, `trend` | Google/TikTok 热词 |
| `product_recommendations` | Phase 1 | `product_id`, `launch_plan(JSON)` | 起盘方案 |
| `influencers` | Phase 2 | `platform`, `influencer_id`, `ai_score`, `status` | 达人库 |
| `outreach_records` | Phase 2 | `influencer_id`, `channel`, `replied` | 招募消息记录 |
| `listings` | Phase 3 | `internal_sku`, `base_title`, `skus(JSON)` | 商品发品基础信息 |
| `platform_listings` | Phase 3 | `listing_id`, `platform`, `status` | 各平台发品状态 |
| `cs_tickets` | Phase 4 | `ticket_type`, `ai_response`, `status` | 客服工单 |
| `daily_metrics` | Phase 5 | `metric_date`, `gmv`, `profit`, `ad_spend` | 每日经营指标 |
| `ai_insights` | Phase 5 | `insight_type`, `priority`, `content` | AI 洞察推送 |
| `task_logs` | 全局 | `task_name`, `phase`, `status`, `duration_ms` | 定时任务执行日志 |

---

### `core/base_agent.py`

所有 AI Agent 的抽象基类，封装 Claude API 工具调用循环。

#### 类：`BaseAgent (ABC)`

**实例变量：**

| 变量 | 类型 | 说明 |
|------|------|------|
| `_client` | `anthropic.Anthropic` | Claude API 客户端 |
| `_history` | `list[dict]` | 对话消息历史（多轮工具调用） |

**抽象属性（子类必须实现）：**

| 属性 | 类型 | 说明 |
|------|------|------|
| `system_prompt` | `str` | 传给 Claude 的系统提示词 |
| `tools` | `list[dict]` | Tool 定义列表（JSON Schema 格式） |

**抽象方法（子类必须实现）：**

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async dispatch_tool(name: str, params: dict) → Any` | `Any` | 根据工具名路由到具体实现 |

**公开方法：**

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async run(user_message: str, fresh: bool = False) → str` | `str` | 执行 Agent 循环（最多 20 轮），返回最终文本响应；`fresh=True` 清空历史 |
| `reset() → None` | `None` | 清空对话历史 |

**工具调用流程（`run` 内部）：**
```
用户消息 → Claude 响应
    ├── stop_reason = "end_turn"  → 返回文本
    └── stop_reason = "tool_use" → dispatch_tool() → 结果追加到 history → 继续循环
```

---

### `core/redis_client.py`

异步 Redis 缓存封装，JSON 序列化存储，默认 TTL 1 小时。

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `async get_redis() → aioredis.Redis` | `Redis` | 返回单例 Redis 客户端（首次调用时初始化） |
| `async cache_set(key: str, value: Any, ttl: int = 3600) → None` | `None` | JSON 序列化后存入 Redis，带 TTL |
| `async cache_get(key: str) → Any \| None` | `Any \| None` | 读取并 JSON 反序列化，Key 不存在返回 `None` |
| `async cache_delete(key: str) → None` | `None` | 删除指定 Key |

---

### `core/scheduler.py`

APScheduler 定时任务调度器，时区 Asia/Shanghai。

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `get_scheduler() → AsyncIOScheduler` | `AsyncIOScheduler` | 返回全局调度器单例 |
| `register_all_jobs() → None` | `None` | 注册 Phase 1 + Phase 2 全部定时任务（见下表） |
| `async start_scheduler() → None` | `None` | 注册任务并启动调度器 |
| `async stop_scheduler() → None` | `None` | 关闭调度器（不等待运行中任务） |

**已注册任务时间表（UTC+8）：**

| 任务 ID | 触发时间 | 对应函数 |
|---------|----------|---------|
| `tiktok_crawl` | 每日 02:00 | `job_crawl_tiktok_trending` |
| `amazon_crawl` | 每日 02:30 | `job_crawl_amazon_bsr` |
| `shopee_crawl` | 每日 03:00 | `job_crawl_shopee_trending` |
| `google_crawl` | 每日 03:30 | `job_crawl_google_trends` |
| `ai_analysis` | 每日 05:00 | `job_ai_discovery_analysis` |
| `tiktok_influencers` | 每日 06:00 | `job_crawl_tiktok_influencers` |
| `youtube_channels` | 每日 06:30 | `job_crawl_youtube_channels` |
| `ai_outreach` | 每日 07:00 | `job_ai_influencer_outreach` |
| `outreach_reply_check` | 每日 12:00 | `job_check_outreach_replies` |

---

## phase1 — 选品发现

---

### `phase1/crawlers/tiktok_crawler.py`

TikTok Shop Open API + Creative Center 爬虫，HMAC-SHA256 签名认证。

#### 类：`TikTokCrawler`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `_sign(path: str, params: dict) → dict` | `dict` | 生成 TikTok API 签名，追加 `sign` 字段到 params |
| `async _get(path: str, params: dict = None) → dict` | `dict` | 签名后发送 GET 请求，返回 JSON |
| `async get_trending_products(category_id: str = "", limit: int = 100) → list[dict]` | `list[dict]` | 抓取热卖商品（按销量降序），mock_mode 时返回模拟数据 |
| `async get_shop_gmv(start_date: str, end_date: str) → dict` | `dict` | 抓取店铺 GMV / 订单 / 转化率，字段：`gmv`, `orders`, `units_sold`, `conversion_rate` |
| `async get_viral_videos(keyword: str = "", limit: int = 50) → list[dict]` | `list[dict]` | 从 Creative Center 抓取爆款视频，含 `views`, `likes`, `gmv_driven` |
| `async get_video_comments_keywords(video_id: str) → list[dict]` | `list[dict]` | 提取视频评论关键词，返回 `[{"keyword": str, "count": int}, ...]` |

**模块级辅助函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_mock_trending_products(limit: int) → list[dict]` | `list[dict]` | 生成 Mock 热卖商品，含随机类目/价格/销量/评分 |
| `_mock_gmv(start: str, end: str) → dict` | `dict` | 生成 Mock GMV 数据 |
| `_mock_viral_videos(limit: int) → list[dict]` | `list[dict]` | 生成 Mock 爆款视频列表 |
| `_mock_comment_keywords() → list[dict]` | `list[dict]` | 返回固定 10 个 Mock 评论关键词 |
| `_extract_keywords(comments: list) → list[dict]` | `list[dict]` | 用正则提取评论词频，去除停用词，返回 Top 30 |

---

### `phase1/crawlers/amazon_crawler.py`

Amazon BSR 爬虫，调用 Rainforest API，真实失败时抛出异常（不静默降级）。

#### 类：`AmazonCrawler`

**常量：** `BSR_CATEGORIES` — 类目名 → BSR 分类 ID 映射（beauty / electronics / home / sports / toys / pet）

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async get_bsr_products(category: str = "beauty", limit: int = 50) → list[dict]` | `list[dict]` | 抓取指定类目 BSR 热销商品；HTTP 失败时 `raise` |
| `async get_new_releases(category: str = "beauty", limit: int = 20) → list[dict]` | `list[dict]` | 抓取新品榜；HTTP 失败时 `raise` |

**模块级辅助函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_normalize_amazon(item: dict) → dict` | `dict` | Rainforest 响应 → 标准商品字段（product_id=ASIN, trend_score=100-rank） |
| `_mock_amazon_products(category: str, limit: int) → list[dict]` | `list[dict]` | 生成 Mock BSR 商品，含随机价格/销量/评分 |

---

### `phase1/crawlers/shopee_crawler.py`

Shopee Open Platform API v2 爬虫，HMAC-SHA256 签名，价格单位 1/100000。

#### 类：`ShopeeCrawler`

**常量：** `BASE = "https://partner.shopeemobile.com/api/v2"`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async get_trending_products(limit: int = 50) → list[dict]` | `list[dict]` | 抓取状态为 NORMAL 的商品列表；HTTP 失败时 `raise` |
| `async get_item_detail(item_id: int, shop_id: int) → dict` | `dict` | 获取单商品详情；失败时 `raise` |

**模块级辅助函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_normalize_shopee(item: dict) → dict` | `dict` | Shopee 响应 → 标准字段（价格 ÷ 100000，提取 review_count） |
| `_mock_shopee_products(limit: int) → list[dict]` | `list[dict]` | 生成 Mock Shopee 商品，含随机类目/价格/销量 |

---

### `phase1/crawlers/google_trends_crawler.py`

Google Trends 爬虫，基于 pytrends 非官方库，支持热搜 / 兴趣曲线 / 相关词。

#### 类：`GoogleTrendsCrawler`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async get_trending_keywords(geo: str = "US", limit: int = 30) → list[dict]` | `list[dict]` | 获取当日热搜词，字段：`keyword`, `platform`, `volume`, `trend`, `geo`, `captured_at` |
| `async get_interest_over_time(keywords: list[str], timeframe: str = "today 3-m", geo: str = "US") → dict` | `dict` | 获取关键词周粒度兴趣曲线（0-100 指数），最多 5 个词；返回 `{keyword: [int, ...]}` |
| `async get_related_queries(keyword: str, geo: str = "US") → dict` | `dict` | 获取 top + rising 相关查询词；返回 `{"top": [...], "rising": [...]}` |

**模块级辅助函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_mock_trends(limit: int) → list[dict]` | `list[dict]` | 从 25 个预置电商关键词中生成 Mock 热搜 |
| `_mock_related_queries(keyword: str) → dict` | `dict` | 返回 Mock top/rising 相关词 |

---

### `phase1/analyzers/product_scorer.py`

利润估算 + 商品多维度评分模型，纯计算模块（无 I/O）。

#### 常量

| 常量 | 说明 |
|------|------|
| `PLATFORM_FEE` | 平台费率字典：TikTok(佣金8%+配送$3.5+广告15%) / Amazon(15%+$5+20%) / Shopee(6%+$2.5+12%) / Lazada / Shopify |

#### 数据类：`ProfitResult`

| 字段 | 类型 | 说明 |
|------|------|------|
| `selling_price` | `float` | 售价（USD） |
| `cost_price` | `float` | 采购成本 |
| `platform_fee` | `float` | 平台佣金 |
| `fulfillment` | `float` | 配送费（含重量系数） |
| `ads_cost` | `float` | 广告费 |
| `gross_profit` | `float` | 毛利润 |
| `profit_rate` | `float` | 利润率 % |
| `profit_grade` | `str` | A/B/C/D（≥40% / ≥25% / ≥10% / <10%） |
| `recommendation` | `str` | 对应等级建议文字 |

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `estimate_profit(selling_price: float, cost_price: Optional[float] = None, platform: str = "tiktok", weight_kg: float = 0.3) → ProfitResult` | `ProfitResult` | 估算利润率；`cost_price` 为 `None` 时默认为售价 30% |

#### 数据类：`ProductScore`

| 字段 | 类型 | 说明 |
|------|------|------|
| `product_id` | `str` | 商品 ID |
| `platform` | `str` | 平台 |
| `trend_score` | `float` | 趋势热度（原始值） |
| `profit_score` | `float` | 利润潜力（0-100） |
| `competition_score` | `float` | 竞争难度（review_count 反向）|
| `market_score` | `float` | 市场容量（sales_volume 正向）|
| `ai_score` | `float` | 加权综合评分 |
| `competition` | `str` | low / medium / high / very_high |
| `market_size` | `str` | small / medium / large / huge |
| `verdict` | `str` | 推荐结论文字 |

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `score_product(product: dict, profit_result: Optional[ProfitResult] = None) → ProductScore` | `ProductScore` | 对单商品评分；权重：趋势35% + 利润30% + 竞争20% + 市场15% |
| `batch_score(products: list[dict], platform: str = "tiktok", top_n: int = 20) → list[ProductScore]` | `list[ProductScore]` | 批量评分，按 ai_score 降序返回 Top N |

---

### `phase1/agents/discovery_agent.py`

AI 选品决策 Agent，继承 `BaseAgent`，含 5 个工具。

#### 类：`DiscoveryAgent(BaseAgent)`

**系统提示词任务（共 5 步）：** 抓取数据 → 评分筛选（≥65）→ 生成起盘方案 → 利润计算 → 保存数据库

**工具定义（`_TOOLS`）：**

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `fetch_trending_data` | `platforms[]`, `category`, `limit_per_platform` | 抓取多平台热销数据 |
| `score_and_filter_products` | `products[]`, `top_n`, `min_score` | 多维评分 + 过滤 |
| `calculate_profit` | `selling_price`, `cost_price?`, `platform`, `weight_kg` | 利润率估算 |
| `save_recommendations` | `recommendations[]` | 入库推荐商品 |
| `get_historical_recommendations` | `days` | 查历史，避免重复推荐 |

**方法：**

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async dispatch_tool(name: str, params: dict) → Any` | `Any` | 路由工具调用 |
| `async _fetch_trending(params: dict) → dict` | `dict` | 并发调用各平台爬虫，返回 `{total_products, products(≤100), trending_keywords, fetched_at}` |
| `def _score_filter(params: dict) → dict` | `dict` | 调用 `batch_score()` + 过滤，返回 `{total_scored, qualified_count, top_products}` |
| `def _calc_profit(params: dict) → dict` | `dict` | 调用 `estimate_profit()`，返回 `asdict(ProfitResult)` |
| `async _save_recs(params: dict) → dict` | `dict` | ON DUPLICATE KEY UPDATE 逐条入库，返回 `{saved, total}` |
| `async _get_history(params: dict) → dict` | `dict` | 查询最近 N 天推荐记录，返回 `{count, products}` |
| `async run_daily_discovery() → str` | `str` | 定时任务入口，调用 `self.run(...)` |

---

### `phase1/scheduler_jobs.py`

Phase 1 定时任务函数，统一通过 `_log_task` 记录执行日志。

| 函数签名 | 触发时间 | 说明 |
|----------|---------|------|
| `async _log_task(name, phase, status, detail, ms) → None` | — | 写入 `task_logs` 表，失败时 `logger.error` |
| `async job_crawl_tiktok_trending() → None` | 02:00 | 抓取 TikTok 热商品（100条）+ 爆款视频（50条） |
| `async job_crawl_amazon_bsr() → None` | 02:30 | 遍历 beauty / electronics / home / sports 4 个类目，各 30 条 |
| `async job_crawl_shopee_trending() → None` | 03:00 | 抓取 Shopee 热销 80 条 |
| `async job_crawl_google_trends() → None` | 03:30 | 抓取 30 个热词并 upsert 到 `trending_keywords` |
| `async job_ai_discovery_analysis() → None` | 05:00 | 调用 `DiscoveryAgent.run_daily_discovery()` |

---

### `phase1/api.py`

Phase 1 FastAPI 路由，前缀 `/api/phase1`。

**常量：** `_VALID_PLATFORMS = {"tiktok", "amazon", "shopee", "google"}`

| 路由 | 方法 | 参数 | 返回值 | 说明 |
|------|------|------|--------|------|
| `/run-discovery` | POST | `category`, `platforms` | `{"status", "result"}` | 立即触发 AI 选品分析 |
| `/recommendations` | GET | `days(1-90)`, `platform?`, `min_score(0-100)`, `limit(1-200)` | `{"count", "data"}` | 获取 AI 推荐商品列表，platform 白名单校验 |
| `/trending-keywords` | GET | `platform?`, `limit(1-200)` | `{"count", "data"}` | 获取热词库 |
| `/profit-calculator` | POST | `selling_price>0`, `cost_price?`, `platform`, `weight_kg≥0` | `ProfitResult as dict` | 利润率估算（含输入校验） |
| `/tiktok-gmv` | GET | `start_date`, `end_date` | `dict` | TikTok Shop GMV 数据 |
| `/google-trends` | GET | `geo`, `limit(1-100)` | `{"count", "data"}` | 实时 Google 热搜词 |
| `/google-trends/interest` | GET | `keywords(逗号分隔≤5)`, `geo`, `timeframe` | `{"keywords", "data"}` | 关键词兴趣趋势曲线 |
| `/task-logs` | GET | `phase`, `limit(1-100)` | `{"count", "data"}` | 任务执行日志 |

---

## phase2 — 达人招募

---

### `phase2/crawlers/influencer_crawler.py`

三平台达人数据爬虫：TikTok Creator Marketplace / YouTube Data API / Instagram Graph API。

#### 类：`TikTokInfluencerCrawler`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `_sign(path: str, params: dict) → dict` | `dict` | HMAC-SHA256 签名 |
| `async _get(base: str, path: str, params: dict = None) → dict` | `dict` | 签名 GET 请求 |
| `async search_influencers(keyword, category, min_followers=10000, max_followers=0, limit=50) → list[dict]` | `list[dict]` | 搜索创作者，失败时返回 mock |
| `async get_influencer_profile(creator_id: str) → dict` | `dict` | 获取达人详细档案（粉丝画像 + 带货历史） |
| `async get_influencer_videos(creator_id: str, limit: int = 20) → list[dict]` | `list[dict]` | 获取达人近期视频（带 GMV 数据） |
| `async get_gmv_leaderboard(category: str = "", limit: int = 30) → list[dict]` | `list[dict]` | 30 天 GMV 带货榜单 |

#### 类：`YouTubeCrawler`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async search_channels(keyword: str, min_subscribers: int = 10000, limit: int = 30) → list[dict]` | `list[dict]` | 搜索频道，两步：先 search 再 fetch statistics；按订阅数过滤 |
| `async get_channel_videos(channel_id: str, limit: int = 10) → list[dict]` | `list[dict]` | 获取频道近期视频 |

#### 类：`InstagramCrawler`

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async get_influencer_insights(ig_user_id: str) → dict` | `dict` | 获取 IG 账号 profile + insights（需授权） |
| `async search_hashtag_creators(hashtag: str, limit: int = 20) → list[dict]` | `list[dict]` | 通过话题标签 Top Media 发现潜力达人 |

**数据标准化函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `_normalize_tiktok_influencer(data: dict) → dict` | `dict` | TikTok API 响应 → 标准达人字段 |
| `_normalize_tiktok_profile(data: dict) → dict` | `dict` | 在 influencer 基础上追加 audience_data + performance |
| `_normalize_youtube_channel(data: dict) → dict` | `dict` | YouTube API 响应 → 标准字段，avg_views = 总播放 / 视频数 |
| `_normalize_instagram(profile: dict, insights: list) → dict` | `dict` | Instagram 响应 → 标准字段，avg_views = 月 reach |

**Mock 数据函数：**

| 函数签名 | 说明 |
|----------|------|
| `_mock_tiktok_influencers(limit: int)` | 生成 4 分级（KOL/Mid/KOC/Nano）混合 Mock 达人，按 GMV 排序 |
| `_mock_tiktok_profile(creator_id: str)` | 生成单个 Mock 达人档案 |
| `_mock_influencer_videos(creator_id: str, limit: int)` | 生成 Mock 视频列表 |
| `_mock_gmv_leaderboard(limit: int)` | GMV 更高的 Mock 榜单 |
| `_mock_youtube_channels(limit: int)` | 生成 Mock YouTube 频道 |
| `_mock_instagram_profile(ig_user_id: str)` | 生成 Mock IG 达人 |
| `_mock_instagram_creators(limit: int)` | 批量 Mock IG 达人 |

---

### `phase2/analyzers/influencer_scorer.py`

达人多维度评分模型，纯计算模块（无 I/O）。

#### 常量

| 常量 | 说明 |
|------|------|
| `INFLUENCER_TIERS` | KOL(≥100万) / 腰部(≥10万) / KOC(≥1万) / 素人(其余)，含佣金区间 |
| `PLATFORM_ER_BENCHMARK` | 平台平均互动率基准：TikTok=3% / YouTube=4% / Instagram=2.5% |

#### 数据类：`InfluencerScore`

| 字段 | 类型 | 说明 |
|------|------|------|
| `influencer_id` | `str` | 平台达人 ID |
| `platform` | `str` | tiktok / youtube / instagram |
| `username` | `str` | 用户名 |
| `tier` | `str` | kol / mid / koc / nano |
| `tier_label` | `str` | 中文等级标签 |
| `followers` | `int` | 粉丝数 |
| `er_score` | `float` | 互动率评分（0-100） |
| `gmv_score` | `float` | 带货力评分（0-100） |
| `audience_score` | `float` | 粉丝质量评分（0-100） |
| `activity_score` | `float` | 内容活跃度（0-100） |
| `ai_score` | `float` | 综合评分（0-100） |
| `contact_available` | `bool` | 是否有 Email 或 WhatsApp |
| `recommended_commission` | `str` | 建议佣金区间，如 `"15%–25%"` |
| `verdict` | `str` | 推荐结论 |
| `outreach_priority` | `str` | high / medium / low |

#### 函数

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `get_tier(followers: int) → tuple[str, str]` | `(tier_key, tier_label)` | 由粉丝数返回等级 |
| `score_influencer(influencer: dict, target_category: str = "") → InfluencerScore` | `InfluencerScore` | 5 维评分：ER(30%) + GMV(35%) + 粉丝质量(20%) + 活跃度(15%) + 类目匹配(+10加分) |
| `batch_score(influencers: list[dict], target_category: str = "", top_n: int = 20, min_score: float = 0) → list[InfluencerScore]` | `list[InfluencerScore]` | 批量评分，过滤 min_score，返回 Top N |
| `generate_outreach_brief(score: InfluencerScore, product_title: str = "") → str` | `str` | 生成达人招募简报文本（供 AI 生成话术时参考） |

**评分细则：**

| 维度 | 权重 | 评分逻辑 |
|------|------|----------|
| GMV 带货力 | 35% | TikTok：按 gmv_30d 分 6 档；其他平台：ER × 0.8 + 粉丝量加分 |
| 互动率 | 30% | ER / 平台基准比值，分 6 档（20-95 分） |
| 粉丝质量 | 20% | avg_views / followers 比值，分 5 档 |
| 内容活跃度 | 15% | 30 天发布视频数，分 6 档；无数据时用 ER × 0.7 |
| 类目匹配 | +10 | 目标类目包含达人类目时加 10 分（上限 100） |

---

### `phase2/agents/influencer_agent.py`

AI 达人招募 Agent，继承 `BaseAgent`，含 7 个工具。

#### 类：`InfluencerAgent(BaseAgent)`

**工具定义（`_TOOLS`）：**

| 工具名 | 参数 | 说明 |
|--------|------|------|
| `search_influencers` | `platforms[]`, `keyword`, `category`, `min_followers`, `max_followers`, `limit` | 多平台搜索达人 |
| `score_and_filter_influencers` | `influencers[]`, `target_category`, `top_n`, `min_score` | 评分 + 过滤 |
| `generate_outreach_message` | `influencer{}`, `product_title`, `product_desc`, `channel`, `commission` | 生成个性化招募话术 |
| `send_outreach` | `influencer_db_id`, `channel`, `message`, `recipient` | 发送 Email / WhatsApp |
| `save_influencers` | `influencers[]` | 达人入库（ON DUPLICATE KEY UPDATE） |
| `get_pipeline_status` | `platform`, `days` | 查看招募漏斗状态 |
| `get_recommended_products` | `limit`, `min_score` | 读取 Phase 1 高分商品 |

**方法：**

| 方法签名 | 返回值 | 说明 |
|----------|--------|------|
| `async dispatch_tool(name: str, params: dict)` | `Any` | 路由工具调用 |
| `async _search_influencers(params: dict) → dict` | `dict` | TikTok：搜索 + GMV 榜去重合并；YouTube/IG 各自爬取；返回 `{total, influencers}` |
| `def _score_filter(params: dict) → dict` | `dict` | `batch_score()` + 过滤，返回 `{total_scored, qualified_count, priority_counts, top_influencers}` |
| `def _generate_message(params: dict) → dict` | `dict` | 按 channel 选模板生成话术，返回 `{channel, recipient, message, brief, generated_at}` |
| `async _send_outreach(params: dict) → dict` | `dict` | 发送消息，写 `outreach_records`，成功时更新达人 status='contacted' |
| `async _save_influencers(params: dict) → dict` | `dict` | 逐条 upsert，返回 `{saved, total, id_map}` |
| `async _get_pipeline(params: dict) → dict` | `dict` | 返回 `{pipeline, total, recent_top10, outreach_sent, outreach_replied}` |
| `async _get_products(params: dict) → dict` | `dict` | 查询 Phase 1 `discovered_products`，返回 `{count, products}` |
| `async run_daily_outreach() → str` | `str` | 定时任务入口 |

**消息模板函数：**

| 函数签名 | 渠道 | 字数限制 |
|----------|------|---------|
| `_email_template(username, product, desc, commission, platform) → str` | Email | ~150 字 |
| `_whatsapp_template(username, product, commission) → str` | WhatsApp | ~80 字 + emoji |
| `_dm_template(username, product, commission, platform) → str` | DM | ~100 字 |

**发送通道函数：**

| 函数签名 | 返回值 | 说明 |
|----------|--------|------|
| `async _send_email(to: str, body: str) → bool` | `bool` | SMTP_SSL 发送，使用 `settings.email` 配置 |
| `async _send_whatsapp(to: str, message: str) → bool` | `bool` | Graph API v19.0，POST `/messages` |
| `def _parse_commission(commission_str: str) → float` | `float` | `"15%–25%"` → `20.0` |

---

### `phase2/scheduler_jobs.py`

Phase 2 定时任务函数。

| 函数签名 | 触发时间 | 说明 |
|----------|---------|------|
| `async _log_task(name, phase, status, detail, ms) → None` | — | 写入 `task_logs`，失败时 `logger.error` |
| `async job_crawl_tiktok_influencers() → None` | 06:00 | 遍历 5 个类目搜索达人 + GMV 榜 |
| `async job_crawl_youtube_channels() → None` | 06:30 | 按 4 个关键词搜索 YouTube 频道 |
| `async job_ai_influencer_outreach() → None` | 07:00 | 调用 `InfluencerAgent.run_daily_outreach()` |
| `async job_check_outreach_replies() → None` | 12:00 | 统计 7 天内未回复的招募记录数 |

---

### `phase2/api.py`

Phase 2 FastAPI 路由，前缀 `/api/phase2`。

**Pydantic 请求体：**

| 模型 | 字段 |
|------|------|
| `OutreachRequest` | `influencer_db_id: int`, `channel: str = "email"`, `product_title: str`, `product_desc: str`, `custom_message: str` |
| `ScoreRequest` | `influencers: list[dict]`, `target_category: str`, `top_n: int = 20`, `min_score: float = 50.0` |

| 路由 | 方法 | 关键参数 | 返回值 | 说明 |
|------|------|---------|--------|------|
| `/run-outreach` | POST | `keyword`, `category`, `platforms` | `{"status", "result"}` | 触发 AI 达人招募任务 |
| `/influencers` | GET | `platform?`, `status?`, `tier?`, `min_score`, `min_followers`, `limit`, `offset` | `{"count", "data"}` | 达人列表（tier 前端过滤） |
| `/influencers/{id}` | GET | `influencer_db_id` | 达人详情 + 招募历史 | 404 if not found |
| `/influencers/score` | POST | `ScoreRequest` | `{"count", "data"}` | 批量评分（不入库） |
| `/outreach/send` | POST | `OutreachRequest` | `{"success", "channel", "recipient", "message"}` | 发送招募消息并入库 |
| `/outreach/{id}/reply` | PATCH | `record_id`, `reply_content` | `{"success": True}` | 标记已回复，更新达人状态为 negotiating |
| `/influencers/{id}/status` | PATCH | `influencer_db_id`, `status` | `{"success", "new_status"}` | 更新达人状态（白名单校验） |
| `/pipeline` | GET | `platform?`, `days` | `{"pipeline", "outreach_sent", "outreach_replied"}` | 招募漏斗总览 |
| `/search-live` | GET | `platform`, `keyword`, `category`, `min_followers`, `limit` | `{"count", "data"}` | 实时搜索 + 评分（不入库） |
| `/outreach-records` | GET | `replied?`, `channel?`, `limit` | `{"count", "data"}` | 招募记录（JOIN influencers） |
| `/task-logs` | GET | `limit` | `{"count", "data"}` | Phase 2 任务日志 |

---

## `main.py`

FastAPI 应用入口，统一挂载所有 Phase 路由。

| 函数/路由 | 说明 |
|-----------|------|
| `lifespan(app: FastAPI)` | 异步上下文管理器；启动时 `init_db()` + `start_scheduler()`；关闭时 `stop_scheduler()` + `close_db()` |
| `GET /` | 返回系统信息字典（名称/版本/所有 Phase API 前缀） |
| `GET /health` | 返回 `{"status": "ok"}` 健康检查 |

**挂载的路由：**
- `phase1_product_discovery.api.router` → `/api/phase1`
- `phase2_influencer.api.router` → `/api/phase2`

---

*本文档由 Claude Code 自动生成，如代码有更新请重新生成。*
