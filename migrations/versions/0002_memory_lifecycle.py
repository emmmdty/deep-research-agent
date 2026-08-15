"""Add provenance and lifecycle fields to product memories."""

import sqlalchemy as sa
from alembic import op

revision = "0002_memory_lifecycle"
down_revision = "0001_product_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("product_memories")}
    additions = {
        "subject_id": sa.Column("subject_id", sa.String(length=128), nullable=True),
        "key": sa.Column("key", sa.String(length=255), nullable=False, server_default=""),
        "provenance": sa.Column(
            "provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")
        ),
        "sensitivity": sa.Column(
            "sensitivity", sa.String(length=16), nullable=False, server_default="normal"
        ),
        "expires_at": sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        "supersedes_memory_id": sa.Column(
            "supersedes_memory_id", sa.String(length=64), nullable=True
        ),
        "confirmed": sa.Column(
            "confirmed", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    }
    for name, column in additions.items():
        if name not in columns:
            op.add_column("product_memories", column)
    if "ix_product_memories_subject_id" not in {
        index["name"] for index in inspector.get_indexes("product_memories")
    }:
        op.create_index(
            "ix_product_memories_subject_id", "product_memories", ["subject_id"], unique=False
        )
    op.execute(
        "UPDATE product_memories SET subject_id = user_id "
        "WHERE subject_id IS NULL AND scope IN ('user_memory', 'agent_experience')"
    )
    op.execute(
        "UPDATE product_memories SET key = scope || ':' || memory_id WHERE key = '' OR key IS NULL"
    )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "ix_product_memories_subject_id" in {
        index["name"] for index in inspector.get_indexes("product_memories")
    }:
        op.drop_index("ix_product_memories_subject_id", table_name="product_memories")
    columns = {column["name"] for column in inspector.get_columns("product_memories")}
    for column in (
        "confirmed",
        "supersedes_memory_id",
        "expires_at",
        "sensitivity",
        "provenance",
        "key",
        "subject_id",
    ):
        if column in columns:
            op.drop_column("product_memories", column)
