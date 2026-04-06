"""
Phase 2 — 达人爬虫
抓取：TikTok 达人数据 / YouTube 频道数据 / Instagram 达人数据
"""
import hashlib
import hmac
import time
from datetime import datetime

import httpx

from core.config import settings
from core.logger import logger


# ══════════════════════════════════════════════════════════════════════════
# TikTok 达人爬虫
# ══════════════════════════════════════════════════════════════════════════
class TikTokInfluencerCrawler:
    """TikTok 达人搜索 + 数据抓取（TikTok Open API / Creator Marketplace）"""

    BASE = "https://open-api.tiktokglobalshop.com"
    CM_BASE = "https://api.tiktok.com/creator_marketplace/v1"

    def __init__(self):
        self.app_key    = settings.tiktok.app_key
        self.app_secret = settings.tiktok.app_secret
        self.token      = settings.tiktok.access_token
        self.shop_id    = settings.tiktok.shop_id

    def _sign(self, path: str, params: dict) -> dict:
        ts = str(int(time.time()))
        p  = {**params, "app_key": self.app_key, "timestamp": ts,
              "access_token": self.token, "shop_id": self.shop_id}
        s  = "".join(f"{k}{v}" for k, v in sorted(p.items()))
        p["sign"] = hmac.new(
            self.app_secret.encode(),
            f"{self.app_secret}{path}{s}{self.app_secret}".encode(),
            hashlib.sha256,
        ).hexdigest().upper()
        return p

    async def _get(self, base: str, path: str, params: dict = None) -> dict:
        signed = self._sign(path, params or {})
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{base}{path}", params=signed)
            return r.json()

    async def search_influencers(
        self,
        keyword: str = "",
        category: str = "",
        min_followers: int = 10000,
        max_followers: int = 0,
        limit: int = 50,
    ) -> list[dict]:
        """搜索达人（Creator Marketplace API）"""
        if settings.mock_mode:
            return _mock_tiktok_influencers(limit)
        params = {
            "keyword":      keyword,
            "category":     category,
            "min_followers": min_followers,
            "page_size":    min(limit, 50),
        }
        if max_followers:
            params["max_followers"] = max_followers
        try:
            data = await self._get(self.CM_BASE, "/creators/search", params)
            creators = data.get("data", {}).get("creators", [])
            return [_normalize_tiktok_influencer(c) for c in creators]
        except Exception as e:
            logger.warning(f"TikTok 达人搜索失败: {e}，返回 mock 数据")
            return _mock_tiktok_influencers(limit)

    async def get_influencer_profile(self, creator_id: str) -> dict:
        """获取达人详细档案（粉丝画像、带货数据）"""
        if settings.mock_mode:
            return _mock_tiktok_profile(creator_id)
        try:
            data = await self._get(self.CM_BASE, f"/creators/{creator_id}/profile", {})
            return _normalize_tiktok_profile(data.get("data", {}))
        except Exception as e:
            logger.warning(f"TikTok 达人档案获取失败 {creator_id}: {e}")
            return _mock_tiktok_profile(creator_id)

    async def get_influencer_videos(self, creator_id: str, limit: int = 20) -> list[dict]:
        """获取达人近期视频（带货表现）"""
        if settings.mock_mode:
            return _mock_influencer_videos(creator_id, limit)
        try:
            data = await self._get(self.CM_BASE, f"/creators/{creator_id}/videos", {
                "page_size": min(limit, 20),
            })
            return data.get("data", {}).get("videos", [])
        except Exception as e:
            logger.warning(f"TikTok 达人视频获取失败 {creator_id}: {e}")
            return _mock_influencer_videos(creator_id, limit)

    async def get_gmv_leaderboard(self, category: str = "", limit: int = 30) -> list[dict]:
        """获取带货 GMV 榜单达人"""
        if settings.mock_mode:
            return _mock_gmv_leaderboard(limit)
        try:
            data = await self._get(self.CM_BASE, "/leaderboard/gmv", {
                "category":  category,
                "page_size": min(limit, 50),
                "period":    "30d",
            })
            creators = data.get("data", {}).get("creators", [])
            return [_normalize_tiktok_influencer(c) for c in creators]
        except Exception as e:
            logger.warning(f"TikTok GMV 榜单获取失败: {e}")
            return _mock_gmv_leaderboard(limit)


# ══════════════════════════════════════════════════════════════════════════
# YouTube 达人爬虫
# ══════════════════════════════════════════════════════════════════════════
class YouTubeCrawler:
    """YouTube Data API v3 — 频道搜索 + 数据抓取"""

    BASE = "https://www.googleapis.com/youtube/v3"

    def __init__(self):
        self.api_key = getattr(settings, "youtube_api_key", "")

    async def search_channels(
        self,
        keyword: str,
        min_subscribers: int = 10000,
        limit: int = 30,
    ) -> list[dict]:
        """按关键词搜索 YouTube 频道"""
        if settings.mock_mode:
            return _mock_youtube_channels(limit)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                # Step 1: 搜索频道
                r = await c.get(f"{self.BASE}/search", params={
                    "key":        self.api_key,
                    "q":          keyword,
                    "type":       "channel",
                    "maxResults": min(limit, 50),
                    "part":       "snippet",
                })
                items = r.json().get("items", [])
                channel_ids = [i["id"]["channelId"] for i in items]
                if not channel_ids:
                    return []

                # Step 2: 批量获取统计
                r2 = await c.get(f"{self.BASE}/channels", params={
                    "key":  self.api_key,
                    "id":   ",".join(channel_ids),
                    "part": "snippet,statistics,brandingSettings",
                })
                channels = r2.json().get("items", [])
                result = [_normalize_youtube_channel(ch) for ch in channels]
                return [c for c in result if c["followers"] >= min_subscribers]
        except Exception as e:
            logger.warning(f"YouTube 搜索失败: {e}，返回 mock 数据")
            return _mock_youtube_channels(limit)

    async def get_channel_videos(self, channel_id: str, limit: int = 10) -> list[dict]:
        """获取频道近期视频"""
        if settings.mock_mode:
            return _mock_influencer_videos(channel_id, limit)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.BASE}/search", params={
                    "key":        self.api_key,
                    "channelId":  channel_id,
                    "order":      "date",
                    "type":       "video",
                    "maxResults": min(limit, 50),
                    "part":       "snippet",
                })
                return r.json().get("items", [])
        except Exception as e:
            logger.warning(f"YouTube 视频获取失败 {channel_id}: {e}")
            return []


# ══════════════════════════════════════════════════════════════════════════
# Instagram 达人爬虫
# ══════════════════════════════════════════════════════════════════════════
class InstagramCrawler:
    """Instagram Graph API — 达人数据（需要 Business/Creator 账号授权）"""

    BASE = "https://graph.facebook.com/v19.0"

    def __init__(self):
        self.access_token = getattr(settings, "instagram_token", "")

    async def get_influencer_insights(self, ig_user_id: str) -> dict:
        """获取 IG 达人洞察数据（仅限已授权账号）"""
        if settings.mock_mode:
            return _mock_instagram_profile(ig_user_id)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.BASE}/{ig_user_id}", params={
                    "fields":       "username,name,biography,followers_count,follows_count,"
                                    "media_count,profile_picture_url,website",
                    "access_token": self.access_token,
                })
                profile = r.json()

                r2 = await c.get(f"{self.BASE}/{ig_user_id}/insights", params={
                    "metric":       "reach,impressions,profile_views",
                    "period":       "month",
                    "access_token": self.access_token,
                })
                insights = r2.json().get("data", [])
                return _normalize_instagram(profile, insights)
        except Exception as e:
            logger.warning(f"Instagram 达人数据获取失败 {ig_user_id}: {e}")
            return _mock_instagram_profile(ig_user_id)

    async def search_hashtag_creators(self, hashtag: str, limit: int = 20) -> list[dict]:
        """通过话题标签发现潜力达人"""
        if settings.mock_mode:
            return _mock_instagram_creators(limit)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                # 搜索话题 ID
                r = await c.get(f"{self.BASE}/ig_hashtag_search", params={
                    "q":            hashtag,
                    "access_token": self.access_token,
                })
                hashtag_id = r.json().get("data", [{}])[0].get("id", "")
                if not hashtag_id:
                    return []

                # 获取近期 Top 媒体
                r2 = await c.get(f"{self.BASE}/{hashtag_id}/top_media", params={
                    "fields":       "id,media_type,owner,like_count,comments_count",
                    "access_token": self.access_token,
                })
                return r2.json().get("data", [])[:limit]
        except Exception as e:
            logger.warning(f"Instagram 话题达人搜索失败: {e}")
            return _mock_instagram_creators(limit)


# ══════════════════════════════════════════════════════════════════════════
# 数据标准化
# ══════════════════════════════════════════════════════════════════════════
def _normalize_tiktok_influencer(data: dict) -> dict:
    import random
    followers = data.get("follower_count", data.get("followers", 0))
    avg_views = data.get("avg_views", int(followers * random.uniform(0.05, 0.3)))
    return {
        "influencer_id":  data.get("creator_id", data.get("id", "")),
        "username":       data.get("unique_id", data.get("username", "")),
        "display_name":   data.get("nickname", data.get("display_name", "")),
        "platform":       "tiktok",
        "followers":      followers,
        "avg_views":      avg_views,
        "avg_engagement": data.get("engagement_rate", round(avg_views / max(followers, 1) * 100, 2)),
        "gmv_30d":        data.get("gmv_30d", 0),
        "category":       data.get("category", ""),
        "content_style":  data.get("content_style", ""),
        "commission_rate": data.get("commission_rate", 0),
        "contact_email":  data.get("email", ""),
        "contact_wa":     data.get("whatsapp", ""),
        "audience_data":  data.get("audience_data", {}),
        "discovered_at":  datetime.now().isoformat(),
    }


def _normalize_tiktok_profile(data: dict) -> dict:
    base = _normalize_tiktok_influencer(data)
    base["audience_data"] = {
        "age_18_24":    data.get("audience_age_18_24", 0),
        "age_25_34":    data.get("audience_age_25_34", 0),
        "female_ratio": data.get("audience_female_ratio", 0),
        "top_countries": data.get("top_countries", []),
    }
    base["performance"] = {
        "videos_30d":   data.get("videos_30d", 0),
        "avg_likes":    data.get("avg_likes", 0),
        "avg_comments": data.get("avg_comments", 0),
        "avg_shares":   data.get("avg_shares", 0),
    }
    return base


def _normalize_youtube_channel(data: dict) -> dict:
    stats = data.get("statistics", {})
    snippet = data.get("snippet", {})
    subs = int(stats.get("subscriberCount", 0))
    views = int(stats.get("viewCount", 0))
    videos = int(stats.get("videoCount", 1))
    return {
        "influencer_id": data.get("id", ""),
        "username":      snippet.get("customUrl", ""),
        "display_name":  snippet.get("title", ""),
        "platform":      "youtube",
        "followers":     subs,
        "avg_views":     views // max(videos, 1),
        "avg_engagement": round(views / max(subs, 1) / max(videos, 1) * 100, 2),
        "gmv_30d":       0,
        "category":      snippet.get("country", ""),
        "content_style": snippet.get("description", "")[:100],
        "contact_email": "",
        "contact_wa":    "",
        "audience_data": {},
        "discovered_at": datetime.now().isoformat(),
    }


def _normalize_instagram(profile: dict, insights: list) -> dict:
    followers = profile.get("followers_count", 0)
    reach = next((i["values"][0]["value"] for i in insights if i.get("name") == "reach"), 0)
    return {
        "influencer_id": profile.get("id", ""),
        "username":      profile.get("username", ""),
        "display_name":  profile.get("name", ""),
        "platform":      "instagram",
        "followers":     followers,
        "avg_views":     reach,
        "avg_engagement": round(reach / max(followers, 1) * 100, 2),
        "gmv_30d":       0,
        "category":      "",
        "content_style": profile.get("biography", "")[:100],
        "contact_email": "",
        "contact_wa":    "",
        "audience_data": {},
        "discovered_at": datetime.now().isoformat(),
    }


# ══════════════════════════════════════════════════════════════════════════
# Mock 数据
# ══════════════════════════════════════════════════════════════════════════
def _mock_tiktok_influencers(limit: int) -> list[dict]:
    import random
    tiers = [
        ("kol",  1000000, 5000000,  50000,  200000, 3.0),
        ("mid",  100000,  999999,   5000,   50000,  5.0),
        ("koc",  10000,   99999,    1000,   8000,   7.0),
        ("nano", 1000,    9999,     200,    1500,   9.0),
    ]
    categories = ["Beauty", "Fashion", "Fitness", "Food", "Tech", "Lifestyle", "Pet", "Home"]
    influencers = []
    for i in range(min(limit, 20)):
        tier_name, min_f, max_f, min_v, max_v, base_er = random.choice(tiers)
        followers = random.randint(min_f, max_f)
        avg_views = random.randint(min_v, max_v)
        cat = random.choice(categories)
        influencers.append({
            "influencer_id":  f"TT_INF_{i+1:05d}",
            "username":       f"creator_{cat.lower()}_{i+1:04d}",
            "display_name":   f"[Mock] {cat} Creator #{i+1}",
            "platform":       "tiktok",
            "followers":      followers,
            "avg_views":      avg_views,
            "avg_engagement": round(base_er + random.uniform(-1, 2), 2),
            "gmv_30d":        round(random.uniform(500, 80000), 2),
            "category":       cat,
            "content_style":  random.choice(["教程/测评", "开箱种草", "日常vlog", "剧情带货"]),
            "commission_rate": round(random.uniform(5, 25), 1),
            "contact_email":  f"creator{i+1}@email.com" if random.random() > 0.4 else "",
            "contact_wa":     f"+1555{random.randint(1000000,9999999)}" if random.random() > 0.5 else "",
            "audience_data":  {
                "age_18_24":    round(random.uniform(25, 50), 1),
                "age_25_34":    round(random.uniform(25, 40), 1),
                "female_ratio": round(random.uniform(40, 80), 1),
                "top_countries": ["US", "GB", "CA"],
            },
            "tier":          tier_name,
            "discovered_at": datetime.now().isoformat(),
        })
    influencers.sort(key=lambda x: x["gmv_30d"], reverse=True)
    return influencers


def _mock_tiktok_profile(creator_id: str) -> dict:
    import random
    followers = random.randint(50000, 2000000)
    return {
        "influencer_id":  creator_id,
        "username":       f"creator_{creator_id[-4:]}",
        "display_name":   f"[Mock] Creator {creator_id[-4:]}",
        "platform":       "tiktok",
        "followers":      followers,
        "avg_views":      random.randint(5000, 200000),
        "avg_engagement": round(random.uniform(2, 10), 2),
        "gmv_30d":        round(random.uniform(1000, 50000), 2),
        "category":       "Beauty",
        "content_style":  "教程/测评",
        "commission_rate": round(random.uniform(8, 20), 1),
        "contact_email":  f"creator@email.com",
        "contact_wa":     "",
        "audience_data":  {
            "age_18_24":    35.0, "age_25_34": 30.0,
            "female_ratio": 72.0, "top_countries": ["US", "GB"],
        },
        "performance": {
            "videos_30d": random.randint(5, 30),
            "avg_likes":  random.randint(1000, 50000),
            "avg_comments": random.randint(100, 5000),
            "avg_shares": random.randint(200, 10000),
        },
        "discovered_at": datetime.now().isoformat(),
    }


def _mock_influencer_videos(creator_id: str, limit: int) -> list[dict]:
    import random
    return [{
        "video_id":    f"VID_{creator_id[-4:]}_{i:03d}",
        "title":       f"Product review video #{i+1}",
        "views":       random.randint(5000, 500000),
        "likes":       random.randint(500, 50000),
        "comments":    random.randint(50, 5000),
        "shares":      random.randint(100, 20000),
        "gmv":         round(random.uniform(0, 10000), 2),
        "created_at":  datetime.now().isoformat(),
    } for i in range(min(limit, 10))]


def _mock_gmv_leaderboard(limit: int) -> list[dict]:
    import random
    influencers = _mock_tiktok_influencers(limit)
    # 榜单上的达人 GMV 更高
    for inf in influencers:
        inf["gmv_30d"] = round(random.uniform(10000, 500000), 2)
    influencers.sort(key=lambda x: x["gmv_30d"], reverse=True)
    return influencers


def _mock_youtube_channels(limit: int) -> list[dict]:
    import random
    topics = ["beauty tutorial", "tech review", "fitness", "cooking", "lifestyle vlog"]
    return [{
        "influencer_id": f"YT_CH_{i+1:05d}",
        "username":      f"channel_{i+1:04d}",
        "display_name":  f"[Mock] YouTube {random.choice(topics).title()} #{i+1}",
        "platform":      "youtube",
        "followers":     random.randint(10000, 2000000),
        "avg_views":     random.randint(5000, 300000),
        "avg_engagement": round(random.uniform(2, 8), 2),
        "gmv_30d":       0,
        "category":      random.choice(topics),
        "content_style": "视频测评",
        "contact_email": f"yt_creator{i+1}@gmail.com" if random.random() > 0.4 else "",
        "contact_wa":    "",
        "audience_data": {},
        "discovered_at": datetime.now().isoformat(),
    } for i in range(min(limit, 15))]


def _mock_instagram_profile(ig_user_id: str) -> dict:
    import random
    followers = random.randint(20000, 1000000)
    return {
        "influencer_id": ig_user_id,
        "username":      f"ig_user_{ig_user_id[-4:]}",
        "display_name":  f"[Mock] IG Creator {ig_user_id[-4:]}",
        "platform":      "instagram",
        "followers":     followers,
        "avg_views":     int(followers * random.uniform(0.05, 0.2)),
        "avg_engagement": round(random.uniform(2, 8), 2),
        "gmv_30d":       0,
        "category":      "Lifestyle",
        "content_style": "图文种草",
        "contact_email": "",
        "contact_wa":    "",
        "audience_data": {},
        "discovered_at": datetime.now().isoformat(),
    }


def _mock_instagram_creators(limit: int) -> list[dict]:
    return [_mock_instagram_profile(f"IG_{i+1:05d}") for i in range(min(limit, 10))]
