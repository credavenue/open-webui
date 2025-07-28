"""Add client_id column to document_chunk table for multi-tenancy

Revision ID: add_client_id_multitenancy
Revises: c69f45358db4
Create Date: 2025-01-23 11:24:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "add_client_id_multitenancy"
down_revision = "9f0c9cd09105"
branch_labels = None
depends_on = None


def upgrade():
    # Add client_id column to document_chunk table
    op.add_column(
        "document_chunk",
        sa.Column("client_id", sa.Text(), nullable=True, index=True),
    )
    
    # Create index on client_id for better query performance
    op.create_index(
        "idx_document_chunk_client_id",
        "document_chunk",
        ["client_id"],
        if_not_exists=True
    )


def downgrade():
    # Drop the index first
    op.drop_index("idx_document_chunk_client_id", "document_chunk")
    
    # Drop the client_id column
    op.drop_column("document_chunk", "client_id")
