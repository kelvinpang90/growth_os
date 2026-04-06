"""
Phase 2 — AI 达人招募决策 Agent
输入：目标商品 + 类目 → 输出：推荐达人列表 + 个性化招募话术 + 发送记录
"""
import json
from dataclasses import asdict
from datetime import datetime

from core.base_agent import BaseAgent, _load_prompt
from core.database import execute, fetchall, fetchone
from core.logger import logger
from phase2_influencer.analyzers.influencer_scorer import (
    batch_score, score_influencer, generate_outreach_brief,
)
from phase2_influencer.crawlers.influencer_crawler import (
    TikTokInfluencerCrawler, YouTubeCrawler, InstagramCrawler,
)

# ── Tool Schemas ──────────────────────────────────────────────────────────
_TOOLS = [
    {
        "name": "search_influencers",
        "description": "从各平台搜索符合条件的达人",
        "input_schema": {
            "type": "object",
            "properties": {
                "platforms": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["tiktok", "youtube", "instagram"]},
                    "description": "要搜索的平台",
                    "default": ["tiktok"]
                },
                "keyword":       {"type": "string",  "description": "搜索关键词（商品类目/风格）", "default": ""},
                "category":      {"type": "string",  "description": "达人类目", "default": ""},
                "min_followers": {"type": "integer", "description": "最低粉丝数", "default": 10000},
                "max_followers": {"type": "integer", "description": "最高粉丝数（0=不限）", "default": 0},
                "limit":         {"type": "integer", "description": "每平台返回数量", "default": 30},
            },
            "required": []
        }
    },
    {
        "name": "score_and_filter_influencers",
        "description": "对达人列表进行多维度评分，筛选出高潜力达人",
        "input_schema": {
            "type": "object",
            "properties": {
                "influencers":      {"type": "array",   "description": "达人列表"},
                "target_category":  {"type": "string",  "description": "目标商品类目", "default": ""},
                "top_n":            {"type": "integer", "description": "返回 Top N", "default": 15},
                "min_score":        {"type": "number",  "description": "最低 AI 评分", "default": 55},
            },
            "required": ["influencers"]
        }
    },
    {
        "name": "generate_outreach_message",
        "description": "为指定达人生成个性化招募话术（Email / WhatsApp / DM）",
        "input_schema": {
            "type": "object",
            "properties": {
                "influencer":    {"type": "object", "description": "达人信息（含评分）"},
                "product_title": {"type": "string", "description": "推广商品名称"},
                "product_desc":  {"type": "string", "description": "商品卖点（50字内）", "default": ""},
                "channel":       {"type": "string", "description": "发送渠道", "enum": ["email", "whatsapp", "dm"], "default": "email"},
                "commission":    {"type": "string", "description": "佣金方案", "default": ""},
            },
            "required": ["influencer", "product_title"]
        }
    },
    {
        "name": "send_outreach",
        "description": "通过 Email 或 WhatsApp 发送招募消息给达人",
        "input_schema": {
            "type": "object",
            "properties": {
                "influencer_db_id": {"type": "integer", "description": "数据库中的达人 ID"},
                "channel":          {"type": "string",  "enum": ["email", "whatsapp", "dm"]},
                "message":          {"type": "string",  "description": "待发送的消息内容"},
                "recipient":        {"type": "string",  "description": "收件人邮箱或 WhatsApp 号码"},
            },
            "required": ["influencer_db_id", "channel", "message", "recipient"]
        }
    },
    {
        "name": "save_influencers",
        "description": "将评分后的达人保存到数据库",
        "input_schema": {
            "type": "object",
            "properties": {
                "influencers": {
                    "type": "array",
                    "description": "达人列表（含评分），每项需有 influencer_id, platform 等字段",
                    "items": {"type": "object"}
                }
            },
            "required": ["influencers"]
        }
    },
    {
        "name": "get_pipeline_status",
        "description": "查询当前达人招募管道状态（各阶段数量）",
        "input_schema": {
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "平台筛选（空=全部）", "default": ""},
                "days":     {"type": "integer", "description": "最近 N 天", "default": 7},
            },
            "required": []
        }
    },
    {
        "name": "get_recommended_products",
        "description": "从 Phase 1 获取待推广的高分商品，作为达人匹配依据",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit":     {"type": "integer", "default": 5},
                "min_score": {"type": "number",  "default": 65},
            },
            "required": []
        }
    },
]


class InfluencerAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return _load_prompt("influencer_system").format(
            date=datetime.now().strftime('%Y-%m-%d')
        )

    @property
    def tools(self) -> list[dict]:
        return _TOOLS

    async def dispatch_tool(self, name: str, params: dict):
        if name == "search_influencers":
            return await self._search_influencers(params)
        elif name == "score_and_filter_influencers":
            return self._score_filter(params)
        elif name == "generate_outreach_message":
            return self._generate_message(params)
        elif name == "send_outreach":
            return await self._send_outreach(params)
        elif name == "save_influencers":
            return await self._save_influencers(params)
        elif name == "get_pipeline_status":
            return await self._get_pipeline(params)
        elif name == "get_recommended_products":
            return await self._get_products(params)
        return {"error": f"未知工具: {name}"}

    # ── Tool 实现 ──────────────────────────────────────────────────────────
    async def _search_influencers(self, params: dict) -> dict:
        platforms    = params.get("platforms", ["tiktok"])
        keyword      = params.get("keyword", "")
        category     = params.get("category", "")
        min_followers = params.get("min_followers", 10000)
        max_followers = params.get("max_followers", 0)
        limit        = params.get("limit", 30)
        all_influencers = []

        for platform in platforms:
            try:
                if platform == "tiktok":
                    # 同时抓搜索结果和 GMV 榜单
                    crawler = TikTokInfluencerCrawler()
                    searched = await crawler.search_influencers(
                        keyword=keyword, category=category,
                        min_followers=min_followers, max_followers=max_followers,
                        limit=limit,
                    )
                    top_gmv = await crawler.get_gmv_leaderboard(category=category, limit=20)
                    combined = {i["influencer_id"]: i for i in searched + top_gmv}
                    all_influencers.extend(combined.values())
                    logger.info(f"TikTok 达人搜索: {len(combined)} 位")

                elif platform == "youtube":
                    channels = await YouTubeCrawler().search_channels(
                        keyword=keyword or category,
                        min_subscribers=min_followers,
                        limit=limit,
                    )
                    all_influencers.extend(channels)
                    logger.info(f"YouTube 达人搜索: {len(channels)} 位")

                elif platform == "instagram":
                    # Instagram 需要已授权账号，通常通过话题标签发现
                    creators = await InstagramCrawler().search_hashtag_creators(
                        hashtag=keyword or category or "beauty",
                        limit=limit,
                    )
                    all_influencers.extend(creators)
                    logger.info(f"Instagram 达人搜索: {len(creators)} 位")

            except Exception as e:
                logger.error(f"{platform} 达人搜索出错: {e}")

        return {
            "total": len(all_influencers),
            "platforms": platforms,
            "influencers": all_influencers,
            "searched_at": datetime.now().isoformat(),
        }

    def _score_filter(self, params: dict) -> dict:
        influencers     = params.get("influencers", [])
        target_category = params.get("target_category", "")
        top_n           = params.get("top_n", 15)
        min_score       = params.get("min_score", 55)

        scored = batch_score(influencers, target_category=target_category,
                             top_n=len(influencers), min_score=0)
        filtered = [s for s in scored if s.ai_score >= min_score][:top_n]

        results = []
        for s in filtered:
            original = next(
                (inf for inf in influencers if inf.get("influencer_id") == s.influencer_id), {}
            )
            results.append({
                **asdict(s),
                "contact_email": original.get("contact_email", ""),
                "contact_wa":    original.get("contact_wa", ""),
                "audience_data": original.get("audience_data", {}),
                "performance":   original.get("performance", {}),
                "gmv_30d":       original.get("gmv_30d", 0),
                "category":      original.get("category", ""),
                "content_style": original.get("content_style", ""),
            })

        # 优先级分层统计
        priority_counts = {"high": 0, "medium": 0, "low": 0}
        for r in results:
            priority_counts[r.get("outreach_priority", "low")] += 1

        return {
            "total_scored":     len(scored),
            "qualified_count":  len(filtered),
            "priority_counts":  priority_counts,
            "top_influencers":  results,
        }

    def _generate_message(self, params: dict) -> dict:
        influencer    = params.get("influencer", {})
        product_title = params.get("product_title", "")
        product_desc  = params.get("product_desc", "")
        channel       = params.get("channel", "email")
        commission    = params.get("commission", influencer.get("recommended_commission", "15%–25%"))

        username     = influencer.get("username", "Creator")
        platform     = influencer.get("platform", "TikTok").upper()
        tier_label   = influencer.get("tier_label", "达人")
        followers    = influencer.get("followers", 0)
        ai_score     = influencer.get("ai_score", 0)

        brief = generate_outreach_brief(
            type("S", (), {
                "username": username,
                "tier_label": tier_label,
                "followers": followers,
                "platform": platform,
                "ai_score": ai_score,
                "verdict": influencer.get("verdict", ""),
                "er_score": influencer.get("er_score", 0),
                "gmv_score": influencer.get("gmv_score", 0),
                "audience_score": influencer.get("audience_score", 0),
                "contact_available": influencer.get("contact_available", False),
                "recommended_commission": commission,
            })(),
            product_title=product_title,
        )

        if channel == "email":
            message = _email_template(username, product_title, product_desc, commission, platform)
        elif channel == "whatsapp":
            message = _whatsapp_template(username, product_title, commission)
        else:
            message = _dm_template(username, product_title, commission, platform)

        return {
            "channel":    channel,
            "recipient":  influencer.get("contact_email" if channel == "email" else "contact_wa", ""),
            "message":    message,
            "brief":      brief,
            "generated_at": datetime.now().isoformat(),
        }

    async def _send_outreach(self, params: dict) -> dict:
        influencer_db_id = params["influencer_db_id"]
        channel   = params["channel"]
        message   = params["message"]
        recipient = params["recipient"]

        if not recipient:
            return {"success": False, "reason": "无有效联系方式"}

        sent = False
        error_msg = ""

        try:
            if channel == "email":
                sent = await _send_email(recipient, message)
            elif channel == "whatsapp":
                sent = await _send_whatsapp(recipient, message)
            else:
                # DM 渠道：记录待发状态，人工跟进
                sent = False
                error_msg = "DM 渠道需人工发送"
        except Exception as e:
            error_msg = str(e)
            logger.error(f"发送招募消息失败 ({channel} → {recipient}): {e}")

        # 记录发送结果
        try:
            await execute("""
                INSERT INTO outreach_records
                    (influencer_id, channel, message, sent_at, replied)
                VALUES (:inf_id, :channel, :msg, NOW(), 0)
            """, {
                "inf_id":  influencer_db_id,
                "channel": channel,
                "msg":     message[:3000],
            })
        except Exception as e:
            logger.error(f"保存招募记录失败: {e}")

        # 更新达人状态为 contacted
        if sent:
            try:
                await execute("""
                    UPDATE influencers SET status = 'contacted', updated_at = NOW()
                    WHERE id = :id
                """, {"id": influencer_db_id})
            except Exception as e:
                logger.error(f"更新达人状态失败: {e}")

        return {
            "success":   sent,
            "channel":   channel,
            "recipient": recipient,
            "reason":    error_msg if not sent else "发送成功",
        }

    async def _save_influencers(self, params: dict) -> dict:
        influencers = params.get("influencers", [])
        saved = 0
        id_map = {}  # influencer_id -> db id

        for inf in influencers:
            try:
                await execute("""
                    INSERT INTO influencers
                        (platform, influencer_id, username, display_name, followers,
                         avg_views, avg_engagement, gmv_30d, category, audience_data,
                         performance, content_style, commission_rate, contact_email,
                         contact_wa, ai_score, status)
                    VALUES
                        (:platform, :inf_id, :username, :display_name, :followers,
                         :avg_views, :avg_engagement, :gmv_30d, :category, :audience_data,
                         :performance, :content_style, :commission_rate, :contact_email,
                         :contact_wa, :ai_score, 'discovered')
                    ON DUPLICATE KEY UPDATE
                        followers=VALUES(followers), avg_views=VALUES(avg_views),
                        avg_engagement=VALUES(avg_engagement), gmv_30d=VALUES(gmv_30d),
                        ai_score=VALUES(ai_score), updated_at=NOW()
                """, {
                    "platform":        inf.get("platform", "tiktok"),
                    "inf_id":          inf.get("influencer_id", "")[:256],
                    "username":        inf.get("username", "")[:256],
                    "display_name":    inf.get("display_name", inf.get("username", ""))[:256],
                    "followers":       inf.get("followers", 0),
                    "avg_views":       inf.get("avg_views", 0),
                    "avg_engagement":  inf.get("avg_engagement", 0),
                    "gmv_30d":         inf.get("gmv_30d", 0),
                    "category":        inf.get("category", "")[:128],
                    "audience_data":   json.dumps(inf.get("audience_data", {}), ensure_ascii=False),
                    "performance":     json.dumps(inf.get("performance", {}), ensure_ascii=False),
                    "content_style":   inf.get("content_style", "")[:256],
                    "commission_rate": _parse_commission(inf.get("recommended_commission", "15%–25%")),
                    "contact_email":   inf.get("contact_email", "")[:256],
                    "contact_wa":      inf.get("contact_wa", "")[:64],
                    "ai_score":        inf.get("ai_score", 0),
                })
                saved += 1

                # 获取刚插入的 ID
                row = await fetchone("""
                    SELECT id FROM influencers
                    WHERE platform = :platform AND influencer_id = :inf_id
                """, {"platform": inf.get("platform", "tiktok"), "inf_id": inf.get("influencer_id", "")})
                if row:
                    id_map[inf.get("influencer_id", "")] = row["id"]

            except Exception as e:
                logger.error(f"保存达人失败 {inf.get('username', '')}: {e}")

        return {"saved": saved, "total": len(influencers), "id_map": id_map}

    async def _get_pipeline(self, params: dict) -> dict:
        platform_clause = ""
        query_params: dict = {"days": params.get("days", 7)}

        if params.get("platform"):
            platform_clause = "AND platform = :platform"
            query_params["platform"] = params["platform"]

        rows = await fetchall(f"""
            SELECT status, COUNT(*) as count
            FROM influencers
            WHERE updated_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            {platform_clause}
            GROUP BY status
        """, query_params)

        pipeline = {r["status"]: r["count"] for r in rows}
        total = sum(pipeline.values())

        recent = await fetchall(f"""
            SELECT id, platform, username, followers, ai_score, status, updated_at
            FROM influencers
            WHERE updated_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            {platform_clause}
            ORDER BY ai_score DESC LIMIT 10
        """, query_params)

        outreach_stats = await fetchone("""
            SELECT COUNT(*) as total,
                   SUM(replied) as replied_count
            FROM outreach_records
            WHERE sent_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
        """, {"days": params.get("days", 7)})

        return {
            "pipeline":       pipeline,
            "total":          total,
            "recent_top10":   recent,
            "outreach_sent":  outreach_stats.get("total", 0) if outreach_stats else 0,
            "outreach_replied": outreach_stats.get("replied_count", 0) if outreach_stats else 0,
        }

    async def _get_products(self, params: dict) -> dict:
        rows = await fetchall("""
            SELECT product_id, platform, title, category, price,
                   sales_volume, trend_score, profit_rate, ai_score, ai_analysis
            FROM discovered_products
            WHERE ai_score >= :min_score
              AND discovered_at >= DATE_SUB(NOW(), INTERVAL 3 DAY)
            ORDER BY ai_score DESC
            LIMIT :limit
        """, {
            "min_score": params.get("min_score", 65),
            "limit":     params.get("limit", 5),
        })
        return {"count": len(rows), "products": rows}

    # ── 便捷入口 ──────────────────────────────────────────────────────────
    async def run_daily_outreach(self) -> str:
        """每日达人招募任务入口"""
        logger.info("开始每日 AI 达人招募分析...")
        return await self.run(
            "请立即执行今日达人招募任务：\n"
            "1. 从 Phase 1 获取今日高分推荐商品\n"
            "2. 在 TikTok 搜索匹配达人（同时搜索 GMV 榜单）\n"
            "3. 评分筛选，保留 AI 评分 ≥ 55 的达人\n"
            "4. 将所有达人保存到数据库\n"
            "5. 为 Top 10 高优先级达人生成个性化招募话术\n"
            "6. 自动发送（有联系方式的达人）\n"
            "7. 输出今日达人招募报告",
            fresh=True
        )


# ── 消息模板 ──────────────────────────────────────────────────────────────
def _email_template(
    username: str,
    product: str,
    desc: str,
    commission: str,
    platform: str,
) -> str:
    desc_line = f"\n商品亮点：{desc}" if desc else ""
    return _load_prompt("email_template").format(
        username=username,
        product=product,
        desc_line=desc_line,
        commission=commission,
        platform=platform,
    )


def _whatsapp_template(username: str, product: str, commission: str) -> str:
    return _load_prompt("whatsapp_template").format(
        username=username,
        product=product,
        commission=commission,
    )


def _dm_template(username: str, product: str, commission: str, platform: str) -> str:
    return _load_prompt("dm_template").format(
        username=username,
        product=product,
        commission=commission,
        platform=platform,
    )


# ── 发送通道 ──────────────────────────────────────────────────────────────
async def _send_email(to: str, body: str) -> bool:
    """通过 SMTP 发送邮件"""
    from core.config import settings as cfg
    try:
        import smtplib
        from email.mime.text import MIMEText
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = "Collaboration Opportunity — Let's Work Together!"
        msg["From"]    = cfg.email.sender
        msg["To"]      = to
        with smtplib.SMTP_SSL(cfg.email.smtp_host, cfg.email.smtp_port) as s:
            s.login(cfg.email.username, cfg.email.password)
            s.send_message(msg)
        logger.info(f"Email 发送成功 → {to}")
        return True
    except Exception as e:
        logger.error(f"Email 发送失败 → {to}: {e}")
        return False


async def _send_whatsapp(to: str, message: str) -> bool:
    """通过 WhatsApp Business API 发送消息"""
    from core.config import settings as cfg
    import httpx
    try:
        phone_id = cfg.whatsapp.phone_number_id
        token    = cfg.whatsapp.access_token
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                f"https://graph.facebook.com/v19.0/{phone_id}/messages",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to":   to.replace("+", "").replace(" ", ""),
                    "type": "text",
                    "text": {"body": message},
                },
            )
            if r.status_code == 200:
                logger.info(f"WhatsApp 发送成功 → {to}")
                return True
            logger.warning(f"WhatsApp 发送失败 → {to}: {r.text}")
            return False
    except Exception as e:
        logger.error(f"WhatsApp 发送失败 → {to}: {e}")
        return False


def _parse_commission(commission_str: str) -> float:
    """从 '15%–25%' 格式解析出中间值"""
    try:
        nums = [float(x.strip().rstrip("%")) for x in commission_str.replace("–", "-").split("-") if x.strip().rstrip("%")]
        return sum(nums) / len(nums) if nums else 0
    except Exception:
        return 0
