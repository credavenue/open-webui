"""Add client_id column to file table for multi-tenancy

Revision ID: b8f2a1c5d9e3
Revises: add_client_id_multitenancy
Create Date: 2025-01-28 15:08:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b8f2a1c5d9e3"
down_revision = "add_client_id_multitenancy"
branch_labels = None
depends_on = None


def upgrade():
    """Add client_id column to file table"""
    op.add_column(
        "file",
        sa.Column("client_id", sa.String(), nullable=True),
    )


def downgrade():
    """Remove client_id column from file table"""
    op.drop_column("file", "client_id")
