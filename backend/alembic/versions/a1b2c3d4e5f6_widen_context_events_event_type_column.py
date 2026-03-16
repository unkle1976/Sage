"""widen context_events event_type column from varchar(50) to varchar(100)

Revision ID: a1b2c3d4e5f6
Revises: d2813747f8c8
Create Date: 2026-03-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd2813747f8c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen event_type from VARCHAR(50) to VARCHAR(100)."""
    op.alter_column(
        'context_events',
        'event_type',
        existing_type=sa.String(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Revert event_type back to VARCHAR(50)."""
    op.alter_column(
        'context_events',
        'event_type',
        existing_type=sa.String(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
