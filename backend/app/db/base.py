"""Declarative base for all SQLAlchemy ORM models.

Business models (Patient, Document, ...) will be added in later tasks and
must inherit from `Base`. For Alembic autogenerate to discover them, every
model module must ultimately be imported from this package.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models of the application."""
