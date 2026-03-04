#!/usr/bin/env python3
import json
import os
from pathlib import Path

SECRETS = Path('/home/safeuser/.clawdbot/secrets')
CAPTCHA_FILE = SECRETS / 'captcha.json'
PROXY_FILE = SECRETS / 'proxies.json'


def check_json(path: Path):
    if not path.exists():
        return False, f'missing: {path}'
    try:
        data = json.loads(path.read_text())
        return True, data
    except Exception as e:
        return False, f'invalid json: {e}'


def main():
    print('=== Marketplace anti-bot preflight ===')

    ok_captcha, captcha = check_json(CAPTCHA_FILE)
    ok_proxy, proxy = check_json(PROXY_FILE)

    if ok_captcha:
        keys = [k for k, v in captcha.items() if isinstance(v, str) and v and not v.startswith('YOUR_')]
        print(f'captcha config: ok ({", ".join(keys) if keys else "no active keys"})')
    else:
        print(f'captcha config: {captcha}')

    if ok_proxy:
        has_rotating = bool(proxy.get('rotating'))
        has_res = bool(proxy.get('residential'))
        print(f'proxy config: ok (rotating={has_rotating}, residential_pool={has_res})')
    else:
        print(f'proxy config: {proxy}')

    env_capsolver = bool(os.getenv('CAPSOLVER_API_KEY'))
    env_2captcha = bool(os.getenv('TWOCAPTCHA_API_KEY'))
    print(f'env CAPSOLVER_API_KEY: {env_capsolver}')
    print(f'env TWOCAPTCHA_API_KEY: {env_2captcha}')

    ready = (ok_proxy and ok_captcha and (env_capsolver or env_2captcha))
    print('ready_for_full_bypass:', ready)


if __name__ == '__main__':
    main()
