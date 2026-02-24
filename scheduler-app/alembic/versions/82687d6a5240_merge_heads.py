"""merge heads

Revision ID: 82687d6a5240
Revises: add_password_reset_fields, ef5ed481bc11
Create Date: 2026-02-21 22:38:18.573408

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '82687d6a5240'
down_revision: Union[str, Sequence[str], None] = ('add_password_reset_fields', 'ef5ed481bc11')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
