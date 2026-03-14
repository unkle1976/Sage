"""update onboarding step values for new flow

Revision ID: d705f154255e
Revises: e4f9aa31db44
Create Date: 2026-03-14 18:56:03.315028

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd705f154255e'
down_revision: Union[str, Sequence[str], None] = 'e4f9aa31db44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update any users stuck on old onboarding steps to new flow."""
    op.execute("""
        UPDATE users
        SET onboarding_step = 'awaiting_first_plant'
        WHERE onboarding_step IN ('awaiting_postcode', 'awaiting_garden_type', 'awaiting_experience', 'awaiting_plants')
        AND onboarding_complete = false
    """)


def downgrade() -> None:
    """Best-effort reverse — set back to awaiting_postcode."""
    op.execute("""
        UPDATE users
        SET onboarding_step = 'awaiting_postcode'
        WHERE onboarding_step = 'awaiting_first_plant'
        AND onboarding_complete = false
    """)
