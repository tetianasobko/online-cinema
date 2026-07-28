"""make external payment id unique

Revision ID: 3fa2d749aeb1
Revises: d94c22de853c
Create Date: 2026-07-28

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3fa2d749aeb1"
down_revision: Union[str, Sequence[str], None] = "d94c22de853c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make Stripe Checkout Session IDs idempotency keys."""
    with op.batch_alter_table("payments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_payments_external_payment_id",
            ["external_payment_id"],
        )


def downgrade() -> None:
    """Remove Stripe Checkout Session ID uniqueness."""
    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_constraint(
            "uq_payments_external_payment_id",
            type_="unique",
        )
