"""Create the multi-user product schema.

Revision ID: 0001_product_schema
Revises:
"""

from alembic import op

from deep_research_agent.product.tables import Base


revision = "0001_product_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
