"""
Compatibility shim — split into separate crawler files; kept to avoid import errors from old references.
Import directly from the new modules:
    from phase1_product_discovery.crawlers.amazon_crawler        import AmazonCrawler
    from phase1_product_discovery.crawlers.shopee_crawler        import ShopeeCrawler
    from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler
"""
from phase1_product_discovery.crawlers.amazon_crawler        import AmazonCrawler
from phase1_product_discovery.crawlers.shopee_crawler        import ShopeeCrawler
from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler

__all__ = ["AmazonCrawler", "ShopeeCrawler", "GoogleTrendsCrawler"]
