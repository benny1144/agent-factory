import os
import sys
import json
import ssl
import socket
from urllib import request, error
from pathlib import Path

# Phase-1 Governance: Localhost-only health check, self-signed certs allowed
# Exit codes:
#   0 -> Healthy
#   2 -> Unauthorized
#   3 -> Unreachable / other error

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_DIR = PROJECT_ROOT / 'junie-bridge'


def load_env_from_file(env_path: Path) -> dict:
    env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding='utf-8').splitlines():
            if not line or line.strip().startswith('#'):
                continue
            if '=' in line:
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def resolve_bridge_config() -> tuple[str, str]:
    # Prefer junie-bridge/.env for bridge runtime settings
    jb_env = load_env_from_file(BRIDGE_DIR / '.env')
    use_https = str(jb_env.get('USE_HTTPS') or os.getenv('USE_HTTPS') or '').lower() == 'true'
    port = int(jb_env.get('PORT') or os.getenv('PORT') or '8765')

    token = (
        jb_env.get('JUNIE_TOKEN')
        or jb_env.get('BRIDGE_TOKEN')
        or os.getenv('JUNIE_TOKEN')
        or os.getenv('BRIDGE_TOKEN')
    )

    scheme = 'https' if use_https else 'http'
    base_url = f"{scheme}://localhost:{port}"
    return base_url, token


def main() -> int:
    base_url, token = resolve_bridge_config()

    url = f"{base_url}/health"
    headers = {}
    if token:
        headers['Authorization'] = f"Bearer {token}"
        headers['X-Junie-Token'] = token  # allow either header server-side

    # Build request
    req = request.Request(url, method='GET', headers=headers)

    # SSL context: allow self-signed (localhost only)
    ctx = None
    if url.startswith('https://'):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    try:
        with request.urlopen(req, context=ctx, timeout=5) as resp:
            status = resp.getcode()
            body = resp.read().decode('utf-8', errors='replace')
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {'raw': body}

            if status == 200 and isinstance(data, dict) and data.get('ok') is True:
                print(f"✅ Junie Bridge Healthy: {json.dumps(data)}")
                return 0
            elif status == 401:
                print("⛔ Unauthorized: Check JUNIE_TOKEN/BRIDGE_TOKEN and TOKEN_REQUIRED settings.")
                return 2
            else:
                print(f"❌ Unexpected response ({status}): {json.dumps(data)}")
                return 3
    except error.HTTPError as e:
        if e.code == 401:
            print("⛔ Unauthorized: Check JUNIE_TOKEN/BRIDGE_TOKEN and TOKEN_REQUIRED settings.")
            return 2
        try:
            body = e.read().decode('utf-8', errors='replace')
        except Exception:
            body = ''
        print(f"❌ HTTP error {e.code}: {body}")
        return 3
    except (error.URLError, socket.timeout, ConnectionError) as e:
        print(f"❌ Unreachable: {e}")
        return 3
    except Exception as e:
        print(f"❌ Error: {e}")
        return 3


if __name__ == '__main__':
    sys.exit(main())
