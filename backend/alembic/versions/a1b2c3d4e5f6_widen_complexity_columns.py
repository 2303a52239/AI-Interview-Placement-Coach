"""widen complexity estimate columns to TEXT

The AI layer returns sentences (e.g. "O(n) - single-pass loop detected."),
which overflowed the original VARCHAR(50) columns on PostgreSQL.

Revision ID: a1b2c3d4e5f6
Revises: 15280c461169
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "15280c461169"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("coding_submissions") as batch:
        batch.alter_column("time_complexity_estimate", existing_type=sa.String(50), type_=sa.Text(), existing_nullable=True)
        batch.alter_column("space_complexity_estimate", existing_type=sa.String(50), type_=sa.Text(), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("coding_submissions") as batch:
        batch.alter_column("time_complexity_estimate", existing_type=sa.Text(), type_=sa.String(50), existing_nullable=True)
        batch.alter_column("space_complexity_estimate", existing_type=sa.Text(), type_=sa.String(50), existing_nullable=True)
