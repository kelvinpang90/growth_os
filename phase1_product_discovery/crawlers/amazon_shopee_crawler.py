"""
兼容性模块 — 已拆分为独立爬虫文件，保留此模块避免旧引用报错。
请直接从新模块导入：
    from phase1_product_discovery.crawlers.amazon_crawler        import AmazonCrawler
    from phase1_product_discovery.crawlers.shopee_crawler        import ShopeeCrawler
    from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler
"""
from phase1_product_discovery.crawlers.amazon_crawler        import AmazonCrawler
from phase1_product_discovery.crawlers.shopee_crawler        import ShopeeCrawler
from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler

__all__ = ["AmazonCrawler", "ShopeeCrawler", "GoogleTrendsCrawler"]
