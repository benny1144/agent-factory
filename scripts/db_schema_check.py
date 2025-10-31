from __future__ import annotations
import os, json
from sqlalchemy import create_engine, inspect
from pathlib import Path
from tools.logging_utils import JsonlLogger
from utils.paths import LOGS_DIR

def run_check() -> dict:
    url = os.environ.get('FACTORY_DB_URL', 'sqlite:///data/factory.db')
    engine = create_engine(url)
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    expected = {'audit_events', 'agent_registry'}
    ok = expected.issubset(tables)
    result = {'ok': ok, 'tables': sorted(tables), 'expected': sorted(expected)}
    logger = JsonlLogger(log_file=LOGS_DIR / 'db_schema_check.jsonl')
    logger.log(ok, {'event': 'db_schema_check', **result})
    return result

if __name__ == '__main__':
    print(json.dumps(run_check()))
