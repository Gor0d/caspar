from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from alembic import command
from alembic.config import Config

from .config import REPO


def database(root, migrate=True):
    engine = create_engine('sqlite:///' + (root / 'caspar.sqlite3').as_posix(), connect_args={'check_same_thread': False})

    @event.listens_for(engine, 'connect')
    def pragmas(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=5000')
        connection.execute('PRAGMA secure_delete=ON')

    if migrate:
        cfg = Config(str(REPO / 'alembic.ini'))
        cfg.set_main_option('script_location', str(REPO / 'migrations'))
        with engine.begin() as connection:
            cfg.attributes['connection'] = connection
            command.upgrade(cfg, 'head')
    import os
    if os.name != 'nt':
        (root / 'caspar.sqlite3').chmod(0o600)
    return engine, sessionmaker(engine, expire_on_commit=False)
