from __future__ import annotations
from pathlib import Path
import json, os

def load_tenant_llm_config(tenant_manifest_path: str | Path) -> dict:
    p = Path(tenant_manifest_path)
    cfg = json.loads(p.read_text(encoding='utf-8'))
    # Resolve env placeholders
    for k,v in list((cfg.get('api_keys') or {}).items()):
        if isinstance(v, str) and v.startswith('<env:') and v.endswith('>'):
            env_name = v[5:-1]
            cfg['api_keys'][k] = os.environ.get(env_name, '')
    return cfg
