from alembic import context
from backend.models import Base

config = context.config


def migrate(connection):
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if config.attributes.get('connection') is not None:
    migrate(config.attributes['connection'])
else:
    from backend.config import Settings
    from sqlalchemy import create_engine
    settings = Settings().prepare()
    engine = create_engine('sqlite:///' + (settings.caspar_data_dir / 'caspar.sqlite3').as_posix())
    with engine.connect() as connection:
        migrate(connection)
