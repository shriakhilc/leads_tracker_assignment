"""initial schema: users, leads, lead_assignments

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-13
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extensions used by the schema.
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    lead_state = postgresql.ENUM("PENDING", "REACHED_OUT", name="lead_state")
    lead_state.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False, server_default=""),
        sa.Column("role", sa.String(), nullable=False, server_default="attorney"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_unique_constraint("uq_users_email", "users", ["email"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("resume_key", sa.String(), nullable=False),
        sa.Column("resume_filename", sa.String(), nullable=False),
        sa.Column("resume_content_type", sa.String(), nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM("PENDING", "REACHED_OUT", name="lead_state", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leads_email", "leads", ["email"])
    op.create_index("ix_leads_state", "leads", ["state"])
    op.create_index("ix_leads_created_at", "leads", ["created_at"])

    op.create_table(
        "lead_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("attorney_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("assigned_by", sa.String(), nullable=False, server_default="SYSTEM"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attorney_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_lead_assignments_lead_id", "lead_assignments", ["lead_id"])
    op.create_index("ix_lead_assignments_attorney_id", "lead_assignments", ["attorney_id"])
    # Invariant: exactly one active assignment per lead.
    op.create_index(
        "uq_lead_assignments_one_active",
        "lead_assignments",
        ["lead_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )


def downgrade() -> None:
    op.drop_table("lead_assignments")
    op.drop_index("ix_leads_created_at", table_name="leads")
    op.drop_index("ix_leads_state", table_name="leads")
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_table("leads")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS lead_state")
