import importlib
import os
from sqlalchemy import create_engine, inspect
from backend.app.config import settings
from backend.app.infrastructure.persistence.database import Base
import backend.app.infrastructure.persistence.models as models_pkg

pkg_dir = os.path.dirname(models_pkg.__file__)
for mod_name in sorted(os.listdir(pkg_dir)):
    if mod_name.endswith('.py') and mod_name != '__init__.py':
        importlib.import_module(f'backend.app.infrastructure.persistence.models.{mod_name[:-3]}')

engine = create_engine(settings.sync_database_url)
inspector = inspect(engine)

tables_db = set(inspector.get_table_names())
expected = {mapper.class_.__tablename__ for mapper in Base.registry.mappers}

print('TABLES_IN_DB')
for name in sorted(tables_db):
    print(name)

print('TABLES_EXPECTED')
for name in sorted(expected):
    print(name)

print('MISSING_TABLES')
for name in sorted(expected - tables_db):
    print(name)

print('EXTRA_TABLES')
for name in sorted(tables_db - expected):
    print(name)

for table_name in sorted(expected & tables_db):
    model_cls = next((mapper.class_ for mapper in Base.registry.mappers if mapper.class_.__tablename__ == table_name), None)
    if model_cls is None:
        continue
    db_cols = {col['name'] for col in inspector.get_columns(table_name)}
    model_cols = {col.name for col in model_cls.__table__.columns}
    missing = model_cols - db_cols
    extra = db_cols - model_cols
    if missing or extra:
        print(f'DRIFT:{table_name}')
        if missing:
            print('MISSING_COLUMNS:' + ','.join(sorted(missing)))
        if extra:
            print('EXTRA_COLUMNS:' + ','.join(sorted(extra)))
