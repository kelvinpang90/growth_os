# Growth OS — 项目架构文档

> 版本：v0.2（Phase 1 + Phase 2 完整实现）
> 更新日期：2026-04-04

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体目录结构](#2-整体目录结构)
3. [分层架构](#3-分层架构)
4. [核心基础设施（core/）](#4-核心基础设施core)
5. [Phase 1 — 选品发现](#5-phase-1--选品发现)
6. [Phase 2 — 达人招募](#6-phase-2--达人招募)
7. [数据流转图](#7-数据流转图)
8. [数据库设计](#8-数据库设计)
9. [定时任务调度](#9-定时任务调度)
10. [AI Agent 设计模式](#10-ai-agent-设计模式)
11. [配置与环境变量](#11-配置与环境变量)
12. [API 接口总览](#12-api-接口总览)
13. [外部依赖与第三方服务](#13-外部依赖与第三方服务)
14. [Phase 路线图](#14-phase-路线图)

---

## 1. 项目概述

**Growth OS** 是一套面向跨境电商卖家的 AI 增长自动化系统，将选品→达人招募→商品上架→客服→数据驾驶舱等核心经营环节用 AI Agent 串联，实现全链路半自动化运营。

**技术栈一览：**

| 层级 | 技术选型 |
|------|----------|
| Web 框架 | FastAPI + Uvicorn (ASGI) |
| AI 引擎 | Anthropic Claude API（工具调用模式） |
| 数据库 | MySQL 8.x（SQLAlchemy 2.x + aiomysql 异步驱动）|
| 缓存 | Redis 7.x（aioredis）|
| 定时任务 | APScheduler 3.x（AsyncIOScheduler）|
| HTTP 客户端 | httpx（全异步）|
| 运行时 | Python 3.11+，asyncio |

---

## 2. 整体目录结构

```
growth_os/
│
├── main.py                          # 应用入口，FastAPI 实例 + 路由注册
├── requirements.txt                 # 依赖清单
│
├── core/                            # ── 基础设施层（所有 Phase 共享）──
│   ├── config.py                    # 全局配置（dataclass + 环境变量）
│   ├── logger.py                    # 统一日志（growth_os logger）
│   ├── database.py                  # 异步 MySQL 连接池 + 全库 DDL
│   ├── base_agent.py                # Claude Agent 抽象基类
│   ├── redis_client.py              # Redis 缓存封装
│   └── scheduler.py                 # APScheduler 实例 + 任务注册
│
├── phase1_product_discovery/        # ── Phase 1：AI 选品 ──
│   ├── crawlers/
│   │   ├── tiktok_crawler.py        # TikTok Shop API
│   │   ├── amazon_crawler.py        # Amazon BSR（Rainforest API）
│   │   ├── shopee_crawler.py        # Shopee Open Platform API v2
│   │   ├── google_trends_crawler.py # Google Trends（pytrends）
│   │   └── amazon_shopee_crawler.py # 兼容性 re-export shim
│   ├── analyzers/
│   │   └── product_scorer.py        # 利润估算 + 商品多维评分
│   ├── agents/
│   │   └── discovery_agent.py       # AI 选品决策 Agent（5 工具）
│   ├── scheduler_jobs.py            # Phase 1 定时任务（5 个）
│   └── api.py                       # FastAPI 路由（/api/phase1）
│
├── phase2_influencer/               # ── Phase 2：AI 达人招募 ──
│   ├── crawlers/
│   │   └── influencer_crawler.py    # TikTok CM / YouTube / Instagram
│   ├── analyzers/
│   │   └── influencer_scorer.py     # 达人多维评分模型
│   ├── agents/
│   │   └── influencer_agent.py      # AI 招募决策 Agent（7 工具）
│   ├── scheduler_jobs.py            # Phase 2 定时任务（4 个）
│   └── api.py                       # FastAPI 路由（/api/phase2）
│
├── phase3_listing/                  # （规划中）商品上架
├── phase4_customer_service/         # （规划中）AI 客服
├── phase5_dashboard/                # （规划中）数据驾驶舱
│
├── migrations/                      # Alembic 迁移（待完善）
├── tests/                           # 测试套件（待完善）
└── docs/
    ├── architecture.md              # 本文档
    └── function_reference.md        # 函数参考文档
```

---

## 3. 分层架构

```
┌─────────────────────────────────────────────────────┐
│                   HTTP API 层                        │
│         FastAPI Routers  /api/phase1  /api/phase2   │
└───────────────────────┬─────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────┐
│                  AI Agent 层                         │
│    DiscoveryAgent          InfluencerAgent           │
│    （5 工具）               （7 工具）                │
│         │                       │                   │
│    BaseAgent（Claude API 工具调用循环，最多 20 轮）    │
└──────┬────────────────────┬────────────────────────-┘
       │                    │
┌──────▼──────┐    ┌────────▼────────┐
│  爬虫层      │    │   分析器层       │
│  Crawlers   │    │   Analyzers     │
│             │    │                 │
│ TikTok      │    │ product_scorer  │
│ Amazon      │    │ influencer_     │
│ Shopee      │    │   scorer        │
│ Google      │    │                 │
│ YouTube     │    │                 │
│ Instagram   │    │                 │
└──────┬──────┘    └────────┬────────┘
       │                    │
┌──────▼────────────────────▼────────────────────────-┐
│                  基础设施层（core/）                   │
│  database.py   redis_client.py   config.py          │
│  logger.py     scheduler.py      base_agent.py      │
└──────────────────────────────────────────────────---┘
                        │
              ┌─────────▼─────────┐
              │  外部服务           │
              │  MySQL · Redis     │
              │  Claude API        │
              │  TikTok/Amazon/    │
              │  Shopee/Google/    │
              │  YouTube/IG API    │
              │  SMTP · WhatsApp   │
              └────────────────────┘
```

---

## 4. 核心基础设施（core/）

### 4.1 配置管理

所有配置通过 `Settings` 单例统一管理，从 `.env` 文件读取，代码内不允许硬编码密钥。

```
.env
 ├── DB_URL
 ├── REDIS_URL
 ├── ANTHROPIC_API_KEY
 ├── TIKTOK_APP_KEY / APP_SECRET / ACCESS_TOKEN / SHOP_ID
 ├── SHOPEE_PARTNER_ID / PARTNER_KEY / ACCESS_TOKEN / SHOP_ID
 ├── AMAZON_ACCESS_KEY
 ├── EMAIL_SMTP_HOST / USERNAME / PASSWORD / SENDER
 ├── WHATSAPP_PHONE_NUMBER_ID / ACCESS_TOKEN
 └── MOCK_MODE=true   ← 开发/测试时启用，所有爬虫返回模拟数据
```

**Mock 模式工作机制：**
- `settings.mock_mode = True` 时，各爬虫类的所有 `get_*` 方法直接返回本地 Mock 数据
- Mock 数据具有随机性（价格/销量/互动率），但结构与真实数据完全一致
- 生产部署时设 `MOCK_MODE=false`，并确保所有 API Key 已配置

### 4.2 数据库连接池

```
create_async_engine(
    pool_size=10,        # 核心连接数
    max_overflow=20,     # 高峰期最多额外 20 个
    pool_recycle=3600,   # 每小时重建连接，防 MySQL 8h 超时断连
    pool_pre_ping=True,  # 使用前 ping，自动剔除失效连接
)
```

所有模块统一通过 `execute / fetchall / fetchone` 三个函数操作数据库，参数化查询防 SQL 注入。

### 4.3 BaseAgent — Claude 工具调用循环

```
用户消息 ──► Claude API (claude-sonnet-4-20250514)
              │
              ├── stop_reason = "end_turn"
              │     └── 返回最终文本
              │
              └── stop_reason = "tool_use"
                    ├── 记录 assistant 消息到 _history
                    ├── for each tool_use block:
                    │     dispatch_tool(name, params)  ← 子类实现
                    │     记录 tool_result 到 _history
                    └── 继续下一轮（最多 20 轮）
```

子类只需实现：
1. `system_prompt` — 告诉 Claude 是什么角色、做什么
2. `tools` — 工具的 JSON Schema 定义
3. `dispatch_tool()` — 工具的实际 Python 实现

---

## 5. Phase 1 — 选品发现

### 5.1 功能边界

| 功能 | 说明 |
|------|------|
| 多平台数据抓取 | TikTok Shop 热卖榜 / Amazon BSR / Shopee 热销 / Google Trends 热词 |
| AI 商品评分 | 趋势(35%) + 利润(30%) + 竞争(20%) + 市场(15%) 四维加权 |
| 利润率估算 | 含平台佣金 / 配送费 / 广告费，支持 5 个平台费率 |
| 起盘方案生成 | Claude 生成：定价策略 / 达人类型 / 视频选题 / GMV 目标 |
| 历史去重 | 查询 7 天内已推荐商品，避免重复推荐 |

### 5.2 数据流

```
定时任务（每日 2:00-5:00）
    │
    ├─ TikTokCrawler.get_trending_products()
    ├─ AmazonCrawler.get_bsr_products()     ──► 原始商品数据
    ├─ ShopeeCrawler.get_trending_products()
    └─ GoogleTrendsCrawler.get_trending_keywords()
              │
              ▼
    DiscoveryAgent._fetch_trending()   ← 汇总（最多 100 条传给 Claude）
              │
              ▼
    DiscoveryAgent._score_filter()
        └─ batch_score() + filter(ai_score ≥ 65)
              │
              ▼
    Claude 生成起盘方案（系统提示词引导）
              │
              ▼
    DiscoveryAgent._save_recs()
        └─ ON DUPLICATE KEY UPDATE → discovered_products 表
```

### 5.3 商品评分模型

```
商品 AI 评分 = trend × 0.35 + profit × 0.30 + competition × 0.20 + market × 0.15

trend_score:      已有字段（爬虫返回，0-100）
profit_score:     estimate_profit(price) → profit_rate × 2（上限 100）
competition_score:
    review_count < 200    → 90分（low）
    review_count < 2000   → 65分（medium）
    review_count < 10000  → 35分（high）
    review_count ≥ 10000  → 15分（very_high）
market_score:
    sales_volume > 20000  → 95分（huge）
    sales_volume > 5000   → 80分（large）
    sales_volume > 1000   → 60分（medium）
    else                  → 35分（small）
```

### 5.4 利润估算模型

```
总成本 = 采购成本 + 平台佣金 + 配送费 + 广告费
利润率 = (售价 - 总成本) / 售价 × 100%

平台费率（佣金% + 配送基础费 + 广告占售价%）：
  TikTok：  8%  + $3.5 + 15%
  Amazon：  15% + $5.0 + 20%
  Shopee：  6%  + $2.5 + 12%
  Lazada：  6%  + $2.8 + 12%
  Shopify:  2%  + $4.0 + 18%

配送费 = 基础费 + 重量 × $1.5/kg
采购成本未知时默认 = 售价 × 30%

利润等级：A(≥40%) · B(≥25%) · C(≥10%) · D(<10%)
```

---

## 6. Phase 2 — 达人招募

### 6.1 功能边界

| 功能 | 说明 |
|------|------|
| 多平台达人搜索 | TikTok Creator Marketplace + GMV 榜 / YouTube 频道 / Instagram 话题标签 |
| AI 达人评分 | 互动率(30%) + GMV(35%) + 粉丝质量(20%) + 活跃度(15%) 四维加权 |
| 达人分级 | KOL(≥100万) / 腰部(10-100万) / KOC(1-10万) / 素人(<1万) |
| 个性化话术 | Claude 驱动，按 Email / WhatsApp / DM 三种渠道生成 |
| 自动发送 | SMTP Email + WhatsApp Business API |
| 招募漏斗管理 | discovered → contacted → negotiating → signed |
| 联动 Phase 1 | 读取高分推荐商品，作为达人类目匹配依据 |

### 6.2 数据流

```
定时任务（每日 6:00-7:00）
    │
    ├─ TikTokInfluencerCrawler.search_influencers()
    ├─ TikTokInfluencerCrawler.get_gmv_leaderboard() ──► 原始达人数据
    └─ YouTubeCrawler.search_channels()
              │
              ▼
    InfluencerAgent._get_products()  ← 从 discovered_products 读取今日高分商品
              │
              ▼
    InfluencerAgent._search_influencers()
              │
              ▼
    InfluencerAgent._score_filter()
        └─ batch_score() + filter(ai_score ≥ 55)
              │
              ├─► InfluencerAgent._save_influencers()
              │       └─ ON DUPLICATE KEY UPDATE → influencers 表
              │
              ▼
    Claude 生成个性化话术（_generate_message 提供简报上下文）
              │
              ▼
    InfluencerAgent._send_outreach()
        ├─ _send_email() / _send_whatsapp()
        └─ INSERT → outreach_records 表
              │
              ▼
    UPDATE influencers SET status = 'contacted'
```

### 6.3 达人评分模型

```
达人 AI 评分 = ER×0.30 + GMV×0.35 + Audience×0.20 + Activity×0.15 + 类目匹配+10

互动率评分（ER Score）：
    ER / 平台基准（TikTok=3%, YouTube=4%, IG=2.5%）
    ≥3倍→95  ≥2倍→85  ≥1.5倍→75  ≥1倍→60  ≥0.5倍→40  其他→20

GMV 带货力评分（TikTok）：
    ≥10万→95  ≥5万→85  ≥1万→70  ≥2000→50  ≥500→35  其他→15
    非 TikTok：ER×0.8 + min(followers/20000, 20)

粉丝质量评分（avg_views / followers）：
    ≥30%→90  ≥15%→75  ≥7%→60  ≥3%→45  其他→25

内容活跃度评分（30天视频数）：
    ≥20→95  ≥12→80  ≥6→65  ≥2→50  ≥1→35  无数据→ER×0.7

招募优先级：
    ai_score≥65 且有联系方式 → high
    ai_score≥65 但无联系方式 → medium
    ai_score 50-65           → medium
    ai_score <50             → low
```

### 6.4 达人招募漏斗

```
discovered（系统发现）
    ↓  自动发送招募消息
contacted（已联系）
    ↓  达人回复
negotiating（洽谈中）
    ↓  签约
signed（已合作）
```

---

## 7. 数据流转图

```
外部平台 API                   Growth OS 内部                   持久化
─────────────────────────────────────────────────────────────────────

TikTok Shop API ──┐
Amazon BSR API ───┼──► Phase1 Crawlers ──► DiscoveryAgent ──► discovered_products
Shopee API ───────┤         │                    │               trending_keywords
Google Trends ────┘         │              Claude AI              product_recommendations
                            │            (工具调用循环)
                            │
TikTok CM API ────┐         │
YouTube API ──────┼──► Phase2 Crawlers ──► InfluencerAgent──► influencers
Instagram API ────┘         │                    │               outreach_records
                            │              Claude AI
                            │            (工具调用循环)
                            │
SMTP / WhatsApp ──────────────────────────────────────────► 外部发件

FastAPI HTTP ─────────────────────────────────────────────► 前端/其他系统
```

---

## 8. 数据库设计

### 8.1 ER 关系图（简化）

```
discovered_products ◄──── product_recommendations
        │
        │ (Phase 1 → Phase 2 数据联动)
        │ InfluencerAgent._get_products() 读取
        ▼
influencers ──────────────► outreach_records
    (1)                          (N)

listings ──────────────────► platform_listings
    (1)                          (N)

cs_tickets（独立，关联 order_id）

daily_metrics（独立时序表）
ai_insights（独立推送表）
task_logs（全局日志）
```

### 8.2 关键索引设计

| 表 | 索引 | 用途 |
|----|------|------|
| `discovered_products` | `idx_score(ai_score DESC)` | 按评分降序分页 |
| `discovered_products` | `idx_discovered(discovered_at)` | 按时间过滤（最近 N 天）|
| `discovered_products` | `uq_platform_product(platform, product_id)` | ON DUPLICATE KEY UPDATE |
| `influencers` | `idx_score(ai_score DESC)` | 按评分排序 |
| `influencers` | `idx_gmv(gmv_30d DESC)` | 按带货 GMV 排序 |
| `influencers` | `uq_platform_influencer` | 去重 |
| `outreach_records` | `idx_influencer(influencer_id)` | 关联查询 |
| `task_logs` | `idx_phase(phase)` | 按 Phase 过滤日志 |

### 8.3 JSON 字段约定

| 表.字段 | 结构 | 说明 |
|---------|------|------|
| `discovered_products.ai_analysis` | `{"launch_plan": {...}}` | 起盘方案 JSON |
| `influencers.audience_data` | `{"age_18_24": %, "female_ratio": %, "top_countries": []}` | 粉丝画像 |
| `influencers.performance` | `{"videos_30d": int, "avg_likes": int, "avg_comments": int}` | 内容表现 |
| `listings.skus` | `[{"sku": str, "color": str, "size": str, "stock": int}]` | SKU 规格 |
| `platform_listings.seo_tags` | `["tag1", "tag2", ...]` | SEO 标签 |

---

## 9. 定时任务调度

```
时间（UTC+8）  任务                        依赖关系
─────────────────────────────────────────────────
02:00        job_crawl_tiktok_trending     无
02:30        job_crawl_amazon_bsr          无
03:00        job_crawl_shopee_trending     无
03:30        job_crawl_google_trends       无
05:00        job_ai_discovery_analysis     ← 依赖 02-03 已完成爬取
                    ↓
             discovered_products 已填充

06:00        job_crawl_tiktok_influencers  无
06:30        job_crawl_youtube_channels    无
07:00        job_ai_influencer_outreach    ← 依赖 05:00 AI 分析已完成
                    ↓
             influencers + outreach_records 已填充

12:00        job_check_outreach_replies    统计待回复数量
```

**任务执行保障：**
- 每个任务都有独立的 try/except，失败不影响其他任务
- 执行结果（含错误信息）写入 `task_logs` 表
- `_log_task` 本身失败时通过 `logger.error` 记录，不再抛出

---

## 10. AI Agent 设计模式

### 10.1 工具设计原则

每个工具遵循 **单一职责**：

| 工具类型 | 职责 | 示例 |
|---------|------|------|
| 数据获取 | 调用外部 API 或数据库查询 | `fetch_trending_data`, `get_recommended_products` |
| 数据计算 | 纯计算，无 I/O | `score_and_filter_products`, `calculate_profit` |
| 数据生成 | 调用 AI 子能力生成内容 | `generate_outreach_message` |
| 数据写入 | 持久化到数据库 | `save_recommendations`, `save_influencers` |
| 执行动作 | 调用外部服务 | `send_outreach` |

### 10.2 工具调用流程（以 DiscoveryAgent 为例）

```
Claude 规划（system_prompt 引导）
    │
    ├─ [tool] fetch_trending_data → 获取原始商品（100条）
    │
    ├─ [tool] score_and_filter_products → 筛选高分商品
    │
    ├─ [tool] calculate_profit(x N) → 逐商品估算利润
    │
    ├─ Claude 生成推荐报告 + 起盘方案（纯文本，在 tool_result 基础上）
    │
    └─ [tool] save_recommendations → 入库
```

### 10.3 防护机制

| 机制 | 实现 |
|------|------|
| 防无限循环 | `BaseAgent.run()` 最多执行 20 轮 |
| 工具错误隔离 | `dispatch_tool` 内部 try/except，返回 `{"error": "..."}` |
| 历史管理 | `fresh=True` 清空 `_history`，定时任务每次全新对话 |
| 输入安全 | API 层白名单校验 platform 参数；profit-calculator 校验数值边界 |

---

## 11. 配置与环境变量

### 必填环境变量

```bash
# 数据库
DB_URL=mysql+aiomysql://user:pass@host:3306/growth_os?charset=utf8mb4

# AI
ANTHROPIC_API_KEY=sk-ant-...

# TikTok（Phase 1 + 2 共用）
TIKTOK_APP_KEY=...
TIKTOK_APP_SECRET=...
TIKTOK_ACCESS_TOKEN=...
TIKTOK_SHOP_ID=...

# Amazon（Phase 1）
AMAZON_ACCESS_KEY=...

# Shopee（Phase 1）
SHOPEE_PARTNER_ID=...
SHOPEE_PARTNER_KEY=...
SHOPEE_ACCESS_TOKEN=...
SHOPEE_SHOP_ID=...
```

### 可选环境变量

```bash
# 开发/测试
MOCK_MODE=true       # 默认 true，生产必须设为 false
DEBUG=false

# Redis（可选，用于缓存）
REDIS_URL=redis://localhost:6379/0

# Phase 2 达人发送
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=...
EMAIL_PASSWORD=...
EMAIL_SENDER=noreply@yourdomain.com

WHATSAPP_PHONE_NUMBER_ID=...
WHATSAPP_ACCESS_TOKEN=...

# YouTube（Phase 2 可选）
YOUTUBE_API_KEY=...

# Instagram（Phase 2 可选）
INSTAGRAM_TOKEN=...
```

---

## 12. API 接口总览

### Phase 1 — `/api/phase1`

| 路由 | 方法 | 说明 |
|------|------|------|
| `/run-discovery` | POST | 触发 AI 选品分析 |
| `/recommendations` | GET | 获取 AI 推荐商品 |
| `/trending-keywords` | GET | 热词库 |
| `/profit-calculator` | POST | 利润率估算 |
| `/tiktok-gmv` | GET | TikTok Shop GMV |
| `/google-trends` | GET | Google 热搜词（实时） |
| `/google-trends/interest` | GET | 关键词兴趣趋势曲线 |
| `/task-logs` | GET | 任务执行日志 |

### Phase 2 — `/api/phase2`

| 路由 | 方法 | 说明 |
|------|------|------|
| `/run-outreach` | POST | 触发 AI 达人招募 |
| `/influencers` | GET | 达人列表（支持多维过滤）|
| `/influencers/{id}` | GET | 达人详情 + 招募历史 |
| `/influencers/score` | POST | 批量评分（不入库）|
| `/influencers/{id}/status` | PATCH | 更新达人状态 |
| `/outreach/send` | POST | 发送招募消息 |
| `/outreach/{id}/reply` | PATCH | 标记已回复 |
| `/pipeline` | GET | 招募漏斗总览 |
| `/search-live` | GET | 实时搜索 + 评分 |
| `/outreach-records` | GET | 招募消息记录 |
| `/task-logs` | GET | Phase 2 任务日志 |

### 系统接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 系统信息（版本/API 列表）|
| `/health` | GET | 健康检查 `{"status": "ok"}` |

---

## 13. 外部依赖与第三方服务

| 服务 | 用途 | Phase | 认证方式 |
|------|------|-------|----------|
| **Anthropic Claude API** | AI 决策核心 | 全部 | API Key |
| **TikTok Open API** | 热卖商品 / 店铺 GMV | 1 | HMAC-SHA256 |
| **TikTok Creator Marketplace API** | 达人搜索 / GMV 榜 | 2 | HMAC-SHA256 |
| **TikTok Creative Center API** | 爆款视频 | 1 | Access Token |
| **Rainforest API** | Amazon BSR 数据 | 1 | API Key |
| **Shopee Open Platform v2** | 热销商品 | 1 | HMAC-SHA256 |
| **Google Trends（pytrends）** | 搜索趋势关键词 | 1 | 无（非官方） |
| **YouTube Data API v3** | 频道数据 | 2 | API Key |
| **Instagram Graph API** | 达人洞察 | 2 | OAuth Token |
| **WhatsApp Business API** | 招募消息发送 | 2 | Bearer Token |
| **SMTP（Gmail 等）** | 招募邮件发送 | 2 | 账号密码 |
| **MySQL 8.x** | 主数据库 | 全部 | 账号密码 |
| **Redis 7.x** | 缓存 | 全部 | 无/密码 |

---

## 14. Phase 路线图

```
Phase 1 ✅  选品发现
    多平台爬虫 + AI 评分 + 利润估算 + 起盘方案生成

Phase 2 ✅  达人招募
    达人发现 + 多维评分 + 个性化话术 + 自动发送

Phase 3 🔲  商品上架（发品）
    规划中：AI 多语言文案生成 + 一键多平台发品
    涉及表：listings, platform_listings

Phase 4 🔲  AI 客服
    规划中：售前 FAQ / 物流查询 / 退款处理 / 评价回复
    涉及表：cs_tickets

Phase 5 🔲  数据驾驶舱
    规划中：GMV / 利润 / 广告 ROI / 达人效果 实时看板
    涉及表：daily_metrics, ai_insights
```

**Phase 3-5 数据库表已提前建好**（`database.py` DDL），待对应 Phase 实现时直接使用。

---

*本文档由 Claude Code 自动生成，如架构有重大变更请更新此文档。*
