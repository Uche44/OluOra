import asyncio
import sys
from os.path import abspath, dirname
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add backend directory to Python path so we can import app modules
sys.path.insert(0, abspath(dirname(dirname(__file__))))

from app.core.config import settings
from app.core.db import Base

# Import all models to ensure they are registered on Base.metadata for autogenerate
from app.modules.waitlist.models import WaitlistEntry
from app.modules.users.models import User, SocialAccount, ApiQuotaUsage
from app.modules.youtube.models import Channel, Video
from app.modules.comments.models import Comment
from app.modules.analysis.models import Analysis, TopicCluster, Insight, AnalysisJob
from app.modules.feedback.models import Feedback
from app.modules.email.models import EmailBatch, EmailMessage

# this is the Alembic Config object
config = context.config

# Set the database URL dynamically from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set metadata target for migrations autogeneration
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    """Callback helper to execute migrations in the synchronous context."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode using async connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = settings.DATABASE_URL

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
