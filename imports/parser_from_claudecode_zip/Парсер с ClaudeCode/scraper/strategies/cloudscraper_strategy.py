"""Стратегия 2: cloudscraper — обходит Cloudflare JS Challenge без браузера."""
import asyncio
import random
from typing import Optional

import cloudscraper

from .base import BaseStrategy, FetchResult
from .requests_strategy import USER_AGENTS


class CloudscraperStrategy(BaseStrategy):
    name = "cloudscraper"

    async def fetch(self, url: str, proxy: Optional[str] = None, timeout: int = 30) -> FetchResult:
        # cloudscraper синхронный — запускаем в executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, url, proxy, timeout)

    def _fetch_sync(self, url: str, proxy: Optional[str], timeout: int) -> FetchResult:
        scraper = cloudscraper.create_scraper(
            browser={
                "browser": "chrome",
                "platform": "windows",
                "mobile": False,
                "desktop": True,
            },
            delay=random.uniform(2, 5),
        )
        scraper.headers.update({"User-Agent": random.choice(USER_AGENTS)})

        proxies = {"http": proxy, "https": proxy} if proxy else None

        try:
            resp = scraper.get(url, proxies=proxies, timeout=timeout, allow_redirects=True)
            html = resp.text

            if self._is_blocked(html, resp.status_code):
                return FetchResult(
                    html=html, url=resp.url,
                    status_code=resp.status_code,
                    strategy_used=self.name,
                    error="blocked",
                )

            return FetchResult(html=html, url=resp.url, status_code=resp.status_code, strategy_used=self.name)
        except Exception as e:
            return FetchResult(html="", url=url, status_code=0, strategy_used=self.name, error=str(e))
