from __future__ import annotations
import os
from sqlalchemy import create_engine
from services.core.db.schema import Base

def main() -> str:
    url = os.environ.get('FACTORY_DB_URL', 'sqlite:///data/factory.db')
    if url.startswith('sqlite:///') and not os.path.exists('data'):
        os.makedirs('data', exist_ok=True)
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    return url

if __name__ == '__main__':
    print(main())
