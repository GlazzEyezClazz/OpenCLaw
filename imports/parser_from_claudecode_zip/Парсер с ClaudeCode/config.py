from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import os


class Settings(BaseSettings):
    anthropic_api_key: str = ""
    proxy_list: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    default_timeout: int = 30
    playwright_timeout: int = 60
    max_concurrent_tasks: int = 5
    max_retries: int = 3

    model_config = {"env_file": ".env", "case_sensitive": False}

    @property
    def proxies(self) -> List[str]:
        if not self.proxy_list:
            return []
        return [p.strip() for p in self.proxy_list.split(",") if p.strip()]


settings = Settings()
