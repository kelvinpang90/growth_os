"""
MySQL async connection pool (SQLAlchemy 2.x + aiomysql)
All modules obtain a session via get_db()
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from core.logger import logger

_engine = None
_session_factory = None


async def init_db() -> None:
    # 初始化 SQLAlchemy 异步引擎和 session 工厂，并创建所有数据库表。
    global _engine, _session_factory
    _engine = create_async_engine(
        settings.db.url,
        echo=settings.debug,
        pool_size=settings.db.pool_size,
        max_overflow=settings.db.max_overflow,
        pool_recycle=settings.db.pool_recycle,
        pool_pre_ping=True,
        connect_args={"charset": "utf8mb4"},
    )
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)
    await _create_all_tables()
    logger.info("MySQL 连接池初始化完成")


async def close_db() -> None:
    # 释放数据库连接池资源。
    global _engine
    if _engine:
        await _engine.dispose()
        logger.info("MySQL 连接池已关闭")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    # 提供事务性 async session 上下文管理器，自动提交或回滚。
    if _session_factory is None:
        await init_db()
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def execute(sql: str, params: dict = None) -> None:
    # 执行不返回结果的 SQL 语句（INSERT/UPDATE/DELETE）。
    async with get_db() as session:
        await session.execute(text(sql), params or {})


async def fetchall(sql: str, params: dict = None) -> list[dict]:
    # 执行 SELECT 并将所有结果行以字典列表形式返回。
    if _session_factory is None:
        await init_db()
    async with _session_factory() as session:
        result = await session.execute(text(sql), params or {})
        rows = result.fetchall()
        keys = list(result.keys())
        return [dict(zip(keys, row)) for row in rows]


async def fetchone(sql: str, params: dict = None) -> dict | None:
    # 执行 SELECT 并返回第一行结果字典，无结果时返回 None。
    rows = await fetchall(sql, params)
    return rows[0] if rows else None


# ── 全库建表 DDL ──────────────────────────────────────────────────────────
_DDL_STATEMENTS = [
    # Phase 1 — 选品
    """
CREATE TABLE `discovered_products`  (
  `id` bigint UNSIGNED NOT NULL AUTO_INCREMENT,
  `platform` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'tiktok/amazon/shopee/google',
  `title` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `category` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `price` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL,
  `currency` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'MYR',
  `sales_volume` varchar(128) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0',
  `gmv_estimate` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0.00',
  `rating` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0.00',
  `review` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0',
  `trend_score` varchar(8) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0.00' COMMENT '趋势热度 0-100',
  `profit_rate` varchar(32) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT '0.00' COMMENT '估算利润率 %',
  `competition` varchar(256) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT 'medium' COMMENT 'low/medium/high',
  `ai_score` decimal(5, 2) NULL DEFAULT 0.00 COMMENT 'AI 综合评分 0-100',
  `ai_analysis` varchar(512) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL DEFAULT NULL COMMENT 'AI 分析结果',
  `raw_data` json NULL,
  `discovered_at` datetime NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`) USING BTREE,
  UNIQUE INDEX `uq_platform_product`(`platform` ASC) USING BTREE,
  INDEX `idx_score`(`ai_score` DESC) USING BTREE,
  INDEX `idx_discovered`(`discovered_at` ASC) USING BTREE,
  INDEX `idx_category`(`category` ASC) USING BTREE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS trending_keywords (
        id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        keyword     VARCHAR(256)    NOT NULL,
        platform    VARCHAR(32)     NOT NULL,
        volume      INT             DEFAULT 0,
        trend       VARCHAR(16)     DEFAULT 'rising' COMMENT 'rising/stable/declining',
        region      VARCHAR(32)     DEFAULT 'global',
        captured_at DATETIME        DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_keyword (keyword(64)),
        INDEX idx_platform (platform),
        INDEX idx_captured (captured_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS product_recommendations (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        product_id      BIGINT UNSIGNED NOT NULL,
        market_size     VARCHAR(32)     COMMENT 'market size',
        profit_rate     DECIMAL(5,2),
        competition     VARCHAR(16),
        influencer_type VARCHAR(128)    COMMENT 'recommended influencer type',
        launch_plan     JSON            COMMENT 'launch plan',
        generated_at    DATETIME        DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_product (product_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # Phase 2 — 达人
    """
    CREATE TABLE IF NOT EXISTS influencers (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        platform        VARCHAR(32)     NOT NULL,
        influencer_id   VARCHAR(256)    NOT NULL,
        username        VARCHAR(256),
        display_name    VARCHAR(256),
        followers       INT             DEFAULT 0,
        avg_views       INT             DEFAULT 0,
        avg_engagement  DECIMAL(5,2)    DEFAULT 0,
        gmv_30d         DECIMAL(14,2)   DEFAULT 0,
        category        VARCHAR(128),
        audience_data   JSON            COMMENT 'audience profile',
        performance     JSON            COMMENT 'sales history',
        content_style   VARCHAR(256),
        commission_rate DECIMAL(5,2)    DEFAULT 0,
        contact_email   VARCHAR(256),
        contact_wa      VARCHAR(64),
        ai_score        DECIMAL(5,2)    DEFAULT 0,
        status          VARCHAR(32)     DEFAULT 'discovered' COMMENT 'discovered/contacted/negotiating/signed',
        updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_platform_influencer (platform, influencer_id(128)),
        INDEX idx_score (ai_score DESC),
        INDEX idx_status (status),
        INDEX idx_gmv (gmv_30d DESC)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS outreach_records (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        influencer_id   BIGINT UNSIGNED NOT NULL,
        channel         VARCHAR(32)     COMMENT 'email/whatsapp/dm',
        message         TEXT,
        sent_at         DATETIME        DEFAULT CURRENT_TIMESTAMP,
        replied         TINYINT(1)      DEFAULT 0,
        reply_content   TEXT,
        replied_at      DATETIME,
        INDEX idx_influencer (influencer_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # Phase 3 — 发品
    """
    CREATE TABLE IF NOT EXISTS listings (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        internal_sku    VARCHAR(128)    NOT NULL UNIQUE,
        base_title      VARCHAR(512),
        base_desc       TEXT,
        images          JSON,
        skus            JSON,
        cost_price      DECIMAL(12,2),
        created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS platform_listings (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        listing_id      BIGINT UNSIGNED NOT NULL,
        platform        VARCHAR(32)     NOT NULL,
        platform_id     VARCHAR(256),
        language        VARCHAR(16)     DEFAULT 'en',
        title           VARCHAR(512),
        description     TEXT,
        price           DECIMAL(12,2),
        status          VARCHAR(32)     DEFAULT 'draft',
        seo_tags        JSON,
        published_at    DATETIME,
        INDEX idx_listing (listing_id),
        INDEX idx_platform (platform)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # Phase 4 — 客服
    """
    CREATE TABLE IF NOT EXISTS cs_tickets (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        platform        VARCHAR(32),
        order_id        VARCHAR(256),
        customer_id     VARCHAR(256),
        ticket_type     VARCHAR(64)     COMMENT 'presale/logistics/refund/review/faq',
        content         TEXT,
        ai_response     TEXT,
        status          VARCHAR(32)     DEFAULT 'open' COMMENT 'open/resolved/escalated',
        resolved_at     DATETIME,
        created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_status (status),
        INDEX idx_type (ticket_type),
        INDEX idx_order (order_id(64))
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # Phase 5 — 驾驶舱
    """
    CREATE TABLE IF NOT EXISTS daily_metrics (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        metric_date     DATE            NOT NULL,
        platform        VARCHAR(32)     NOT NULL,
        gmv             DECIMAL(14,2)   DEFAULT 0,
        orders          INT             DEFAULT 0,
        profit          DECIMAL(14,2)   DEFAULT 0,
        ad_spend        DECIMAL(12,2)   DEFAULT 0,
        ad_revenue      DECIMAL(12,2)   DEFAULT 0,
        refund_amount   DECIMAL(12,2)   DEFAULT 0,
        refund_rate     DECIMAL(5,2)    DEFAULT 0,
        influencer_gmv  DECIMAL(14,2)   DEFAULT 0,
        new_customers   INT             DEFAULT 0,
        created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY uq_date_platform (metric_date, platform),
        INDEX idx_date (metric_date)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_insights (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        insight_type    VARCHAR(64),
        content         TEXT,
        priority        VARCHAR(16)     DEFAULT 'normal' COMMENT 'urgent/high/normal/low',
        generated_at    DATETIME        DEFAULT CURRENT_TIMESTAMP,
        is_read         TINYINT(1)      DEFAULT 0,
        INDEX idx_priority (priority),
        INDEX idx_generated (generated_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # 用户认证
    """
    CREATE TABLE IF NOT EXISTS users (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        username        VARCHAR(64)     NOT NULL UNIQUE,
        email           VARCHAR(256)    NOT NULL UNIQUE,
        password_hash   VARCHAR(256)    NOT NULL,
        platform        ENUM('tiktok','shopee','amazon') NOT NULL COMMENT 'bound platform (unique)',
        language        ENUM('zh','en')  DEFAULT 'en'  COMMENT 'UI language',
        currency        ENUM('CNY','MYR') DEFAULT 'MYR' COMMENT 'currency preference',
        is_active       TINYINT(1)      DEFAULT 1,
        created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
        updated_at      DATETIME        DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_email (email),
        INDEX idx_platform (platform)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS refresh_tokens (
        id              BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        user_id         BIGINT UNSIGNED NOT NULL,
        token_hash      VARCHAR(64)     NOT NULL UNIQUE COMMENT 'SHA256(raw_token)',
        expires_at      DATETIME        NOT NULL,
        created_at      DATETIME        DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user (user_id),
        INDEX idx_expires (expires_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    # 通用任务日志
    """
    CREATE TABLE IF NOT EXISTS task_logs (
        id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
        task_name   VARCHAR(128),
        phase       VARCHAR(32),
        status      VARCHAR(32)     COMMENT 'running/success/failed',
        detail      TEXT,
        duration_ms INT,
        started_at  DATETIME        DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_task (task_name),
        INDEX idx_phase (phase),
        INDEX idx_started (started_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
]


async def _create_all_tables() -> None:
    # 依次执行 DDL 语句，创建所有业务数据库表（IF NOT EXISTS）。
    if _engine is None:
        return
    async with _engine.begin() as conn:
        for ddl in _DDL_STATEMENTS:
            await conn.execute(text(ddl))
    logger.info(f"数据库表初始化完成（共 {len(_DDL_STATEMENTS)} 张表）")
