"""Allow campaigns connected from Keitaro without creation metadata."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5d81a6c2e4f7"
down_revision: str | Sequence[str] | None = "bcce43999781"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.alter_column("geo", existing_type=sa.JSON(), nullable=True)
        batch_op.alter_column("offer_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("geo_stream_id", existing_type=sa.Integer(), nullable=True)
        batch_op.alter_column("offer_stream_id", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute(
        "DELETE FROM stream_offers WHERE stream_id IN "
        "(SELECT id FROM streams WHERE campaign_id IN "
        "(SELECT keitaro_id FROM campaigns WHERE geo IS NULL OR offer_id IS NULL))"
    )
    op.execute(
        "DELETE FROM streams WHERE campaign_id IN "
        "(SELECT keitaro_id FROM campaigns WHERE geo IS NULL OR offer_id IS NULL)"
    )
    op.execute("DELETE FROM campaigns WHERE geo IS NULL OR offer_id IS NULL")
    with op.batch_alter_table("campaigns") as batch_op:
        batch_op.alter_column("offer_stream_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("geo_stream_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("offer_id", existing_type=sa.Integer(), nullable=False)
        batch_op.alter_column("geo", existing_type=sa.JSON(), nullable=False)
