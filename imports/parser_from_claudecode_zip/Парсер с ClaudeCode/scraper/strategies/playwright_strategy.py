"""
Стратегия 3: Playwright Stealth — полноценный браузер с обходом антибот-систем.
Обходит: Cloudflare, DataDome, Akamai, PerimeterX, Shape Security и др.
"""
import asyncio
import random
from typing import Optional

from playwright.async_api import async_playwright, Page, BrowserContext

from .base import BaseStrategy, FetchResult
from .requests_strategy import USER_AGENTS

# Скрипт для скрытия признаков автоматизации
STEALTH_SCRIPT = """
() => {
    // Скрываем webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // Подделываем plugins
    Object.defineProperty(navigator, 'plugins', {
        get: () => {
            const plugins = [
                { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                { name: 'Native Client', filename: 'internal-nacl-plugin' },
            ];
            plugins.refresh = () => {};
            plugins.item = (i) => plugins[i];
            plugins.namedItem = (name) => plugins.find(p => p.name === name);
            Object.setPrototypeOf(plugins, PluginArray.prototype);
            return plugins;
        }
    });

    // Подделываем languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['ru-RU', 'ru', 'en-US', 'en']
    });

    // Скрываем chrome.runtime.id (признак расширений/автоматизации)
    if (window.chrome && window.chrome.runtime) {
        Object.defineProperty(window.chrome.runtime, 'id', { get: () => undefined });
    }

    // Подделываем permissions
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (params) =>
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(params);

    // Убираем признак headless через User-Agent
    Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });
    Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });

    // WebGL fingerprint — скрываем точный рендерер
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {
        if (parameter === 37445) return 'Intel Inc.';
        if (parameter === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, parameter);
    };

    // Убираем HeadlessChrome из UA в window.navigator
    Object.defineProperty(navigator, 'userAgent', {
        get: () => navigator.userAgent.replace('HeadlessChrome', 'Chrome')
    });

    // Fake battery API
    if (navigator.getBattery) {
        navigator.getBattery = () => Promise.resolve({
            charging: true, chargingTime: 0,
            dischargingTime: Infinity, level: 1,
        });
    }
}
"""

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 800},
]


class PlaywrightStrategy(BaseStrategy):
    name = "playwright"

    async def fetch(self, url: str, proxy: Optional[str] = None, timeout: int = 60) -> FetchResult:
        proxy_config = None
        if proxy:
            # Парсим формат http://user:pass@host:port
            proxy_config = {"server": proxy}
            if "@" in proxy:
                creds, server = proxy.rsplit("@", 1)
                scheme = creds.split("://")[0]
                user_pass = creds.split("://")[1]
                username, password = user_pass.split(":", 1)
                proxy_config = {
                    "server": f"{scheme}://{server}",
                    "username": username,
                    "password": password,
                }

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                    "--start-maximized",
                    "--disable-extensions",
                    "--no-first-run",
                    "--ignore-certificate-errors",
                ],
            )

            viewport = random.choice(VIEWPORTS)
            user_agent = random.choice(USER_AGENTS)

            context: BrowserContext = await browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                proxy=proxy_config,
                ignore_https_errors=True,
                java_script_enabled=True,
                extra_http_headers={
                    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
                    "DNT": "1",
                },
            )

            # Внедряем stealth-скрипт при каждой загрузке страницы
            await context.add_init_script(STEALTH_SCRIPT)

            page: Page = await context.new_page()

            # Имитируем человека: случайное движение мыши при загрузке
            page.on("domcontentloaded", lambda: asyncio.ensure_future(self._human_mouse(page)))

            try:
                response = await page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=timeout * 1000,
                )

                # Ждём немного как человек
                await asyncio.sleep(random.uniform(1.5, 3.5))

                # Если есть CAPTCHA — пробуем подождать дольше
                html = await page.content()
                if self._is_captcha(html):
                    await asyncio.sleep(random.uniform(3, 6))
                    html = await page.content()

                status_code = response.status if response else 0
                final_url = page.url

                if self._is_blocked(html, status_code):
                    return FetchResult(
                        html=html, url=final_url,
                        status_code=status_code,
                        strategy_used=self.name,
                        error="blocked",
                    )

                return FetchResult(html=html, url=final_url, status_code=status_code, strategy_used=self.name)

            except Exception as e:
                return FetchResult(html="", url=url, status_code=0, strategy_used=self.name, error=str(e))
            finally:
                await browser.close()

    async def _human_mouse(self, page: Page):
        """Случайные движения мыши для имитации человека."""
        try:
            for _ in range(random.randint(2, 5)):
                await page.mouse.move(
                    random.randint(100, 1200),
                    random.randint(100, 700),
                )
                await asyncio.sleep(random.uniform(0.1, 0.4))
        except Exception:
            pass

    def _is_captcha(self, html: str) -> bool:
        patterns = ["captcha", "recaptcha", "hcaptcha", "turnstile", "verify you are human"]
        lower = html.lower()
        return any(p in lower for p in patterns)
