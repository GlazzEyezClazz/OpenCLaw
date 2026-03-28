"""Базовый класс стратегии парсинга."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class FetchResult:
    html: str
    url: str                  # финальный URL (после редиректов)
    status_code: int
    strategy_used: str
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None and bool(self.html)


class BaseStrategy(ABC):
    name: str = "base"

    @abstractmethod
    async def fetch(self, url: str, proxy: Optional[str] = None, timeout: int = 30) -> FetchResult:
        ...

    def _is_blocked(self, html: str, status_code: int) -> bool:
        """Эвристика: определяем, заблокировал ли нас сайт."""
        if status_code in (403, 429, 503):
            return True
        blocked_patterns = [
            "access denied", "403 forbidden", "cloudflare",
            "please enable javascript", "captcha", "bot detected",
            "verify you are human", "ddos-guard", "just a moment",
            "enable cookies", "security check",
        ]
        lower = html.lower()
        # Коротко + содержит паттерн блокировки = заблокирован
        if len(html) < 5000:
            for p in blocked_patterns:
                if p in lower:
                    return True
        return False
