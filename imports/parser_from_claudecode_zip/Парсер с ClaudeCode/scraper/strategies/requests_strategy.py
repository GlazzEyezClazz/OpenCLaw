"""Стратегия 1: httpx — быстро, без браузера. Работает для большинства простых сайтов."""
import httpx
import random
from typing import Optional

from .base import BaseStrategy, FetchResult

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
]

HEADERS_BASE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
}


class RequestsStrategy(BaseStrategy):
    name = "httpx"

    async def fetch(self, url: str, proxy: Optional[str] = None, timeout: int = 30) -> FetchResult:
        headers = {**HEADERS_BASE, "User-Agent": random.choice(USER_AGENTS)}
        proxies = {"http://": proxy, "https://": proxy} if proxy else None

        try:
            async with httpx.AsyncClient(
                headers=headers,
                proxies=proxies,
                follow_redirects=True,
                timeout=timeout,
                verify=False,
                http2=True,
            ) as client:
                resp = await client.get(url)
                html = resp.text

                if self._is_blocked(html, resp.status_code):
                    return FetchResult(
                        html=html, url=str(resp.url),
                        status_code=resp.status_code,
                        strategy_used=self.name,
                        error="blocked",
                    )

                return FetchResult(
                    html=html, url=str(resp.url),
                    status_code=resp.status_code,
                    strategy_used=self.name,
                )
        except Exception as e:
            return FetchResult(html="", url=url, status_code=0, strategy_used=self.name, error=str(e))
