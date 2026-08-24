"""Alembic migration environment.

The database URL is taken from application settings (environment variables
/ .env), so alembic.ini never contains real credentials and there is a
single source of truth for configuration.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.db.base import Base

import app.models  # noqa: F401  (registers ORM models on Base.metadata)

# Alembic Config object — provides access to values in alembic.ini.
config = context.config

# Set up Python loggers from the alembic.ini config section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the real database URL from application settings.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Target metadata for 'autogenerate' support. Business models (added in
# later tasks) must be imported into app.db.base for Alembic to see them.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine — SQL is
    emitted to the script output directly.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode — with a live database connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
