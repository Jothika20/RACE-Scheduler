"""remove direct permission columns from users table

Revision ID: 7393157a3cce
Revises: 28cb5c0b7b33
Create Date: 2025-11-07 11:16:38.304005

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7393157a3cce'
down_revision: Union[str, Sequence[str], None] = '28cb5c0b7b33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("can_create_events")
        batch_op.drop_column("can_create_users")

def downgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("can_create_events", sa.Boolean(), default=False))
        batch_op.add_column(sa.Column("can_create_users", sa.Boolean(), default=False))
