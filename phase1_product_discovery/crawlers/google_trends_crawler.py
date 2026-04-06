"""
Phase 1 — Google Trends 爬虫
抓取：实时热搜关键词 / 关键词兴趣趋势曲线
依赖：pytrends（非官方库，速率限制较严，生产环境建议加 Redis 缓存）
"""
import random
from datetime import datetime

from core.config import settings
from core.logger import logger


class GoogleTrendsCrawler:

    async def get_trending_keywords(self, geo: str = "US", limit: int = 30) -> list[dict]:
        """获取 Google 当日热搜关键词"""
        if settings.mock_mode:
            return _mock_trends(limit)
        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30), retries=2, backoff_factor=0.5)
            df = pt.trending_searches(pn=geo.lower())
            return [
                {
                    "keyword":     str(row),
                    "platform":    "google",
                    "volume":      0,              # trending_searches 不返回 volume
                    "trend":       "rising",
                    "geo":         geo,
                    "captured_at": datetime.now().isoformat(),
                }
                for row in df[0].head(limit)
            ]
        except Exception as e:
            logger.error(f"Google Trends 热搜抓取失败 geo={geo}: {e}")
            raise

    async def get_interest_over_time(
        self,
        keywords: list[str],
        timeframe: str = "today 3-m",
        geo: str = "US",
    ) -> dict:
        """
        获取关键词近期搜索兴趣曲线（周粒度，最多 5 个关键词）。
        返回：{keyword: [weekly_index, ...], ...}  index 范围 0-100
        """
        if not keywords:
            return {}
        if settings.mock_mode:
            return {kw: [random.randint(20, 100) for _ in range(13)] for kw in keywords}
        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30), retries=2, backoff_factor=0.5)
            pt.build_payload(keywords[:5], timeframe=timeframe, geo=geo)
            df = pt.interest_over_time()
            if df.empty:
                logger.warning(f"Google Trends 返回空数据 keywords={keywords}")
                return {}
            return {col: df[col].tolist() for col in df.columns if col != "isPartial"}
        except Exception as e:
            logger.error(f"Google Trends 兴趣曲线抓取失败 keywords={keywords}: {e}")
            raise

    async def get_related_queries(self, keyword: str, geo: str = "US") -> dict:
        """
        获取关键词的相关查询词（top + rising）。
        适合发现长尾词和新兴需求。
        """
        if settings.mock_mode:
            return _mock_related_queries(keyword)
        try:
            from pytrends.request import TrendReq
            pt = TrendReq(hl="en-US", tz=360, timeout=(10, 30), retries=2, backoff_factor=0.5)
            pt.build_payload([keyword], timeframe="today 1-m", geo=geo)
            related = pt.related_queries()
            result = {}
            if keyword in related:
                for kind in ("top", "rising"):
                    df = related[keyword].get(kind)
                    if df is not None and not df.empty:
                        result[kind] = df.head(10).to_dict("records")
            return result
        except Exception as e:
            logger.error(f"Google Trends 相关词抓取失败 keyword={keyword}: {e}")
            raise


# ── Mock 数据 ─────────────────────────────────────────────────────────────
_MOCK_KEYWORDS = [
    "wireless earbuds", "led strip lights", "portable blender", "resistance bands",
    "posture corrector", "facial roller", "air purifier", "smart watch", "yoga mat",
    "shower head", "phone stand", "desk organizer", "silk pillowcase", "beard trimmer",
    "electric toothbrush", "massage gun", "ring light", "laptop stand", "ice roller",
    "jump rope", "water bottle", "coffee frother", "nail kit", "body scrub", "hair clips",
]


def _mock_trends(limit: int) -> list[dict]:
    return [
        {
            "keyword":     _MOCK_KEYWORDS[i % len(_MOCK_KEYWORDS)],
            "platform":    "google",
            "volume":      random.randint(10000, 5000000),
            "trend":       random.choice(["rising", "rising", "stable"]),
            "geo":         "US",
            "captured_at": datetime.now().isoformat(),
        }
        for i in range(min(limit, len(_MOCK_KEYWORDS)))
    ]


def _mock_related_queries(keyword: str) -> dict:
    return {
        "top": [
            {"query": f"{keyword} review", "value": 100},
            {"query": f"best {keyword}", "value": 85},
            {"query": f"{keyword} for beginners", "value": 72},
        ],
        "rising": [
            {"query": f"{keyword} 2025", "value": 5000},
            {"query": f"cheap {keyword}", "value": 350},
        ],
    }
