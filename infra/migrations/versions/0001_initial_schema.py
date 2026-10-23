"""initial ontology engine schema (objects, staging, resolutions, audit, embeddings, evals, agent)

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-23

Embedding dimension defaults to 384 (local sentence-transformers MiniLM). If the deployed embedding
provider emits a different dimension (e.g. voyage-3 = 1024), change EMBEDDING_DIM and re-stamp.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "staging_records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("source_key", sa.String(), index=True),
        sa.Column("external_id", sa.String(), index=True),
        sa.Column("status", sa.String(), index=True),
        sa.Column("data", JSONB(), nullable=False),
    )

    op.create_table(
        "object_instances",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("object_type_key", sa.String(), index=True),
        sa.Column("is_fused", sa.Boolean(), index=True, server_default=sa.false()),
        sa.Column("data", JSONB(), nullable=False),
    )

    op.create_table(
        "resolution_decisions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("instance_id", sa.String(), index=True),
        sa.Column("data", JSONB(), nullable=False),
    )

    op.create_table(
        "action_attempts",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("action_key", sa.String(), index=True),
        sa.Column("idempotency_key", sa.String(), index=True),
        sa.Column("mode", sa.String(), index=True),
        sa.Column("status", sa.String(), index=True),
        sa.Column("data", JSONB(), nullable=False),
    )

    op.execute(
        f"""
        CREATE TABLE embeddings (
            instance_id      VARCHAR PRIMARY KEY,
            object_type_key  VARCHAR,
            vector           vector({EMBEDDING_DIM}),
            data             JSONB NOT NULL
        )
        """
    )
    op.create_index("ix_embeddings_object_type_key", "embeddings", ["object_type_key"])

    op.create_table(
        "golden_cases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), index=True),  # match | non_match
        sa.Column("data", JSONB(), nullable=False),
    )

    op.create_table(
        "agent_interactions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("trace_id", sa.String(), index=True),
        sa.Column("data", JSONB(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_interactions")
    op.drop_table("golden_cases")
    op.drop_index("ix_embeddings_object_type_key", table_name="embeddings")
    op.drop_table("embeddings")
    op.drop_table("action_attempts")
    op.drop_table("resolution_decisions")
    op.drop_table("object_instances")
    op.drop_table("staging_records")
    op.execute("DROP EXTENSION IF EXISTS vector")
