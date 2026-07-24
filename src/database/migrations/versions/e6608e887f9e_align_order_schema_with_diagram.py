"""align order schema with diagram

Revision ID: e6608e887f9e
Revises: 944ebe8db918
Create Date: 2026-07-24 19:24:20.408676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6608e887f9e'
down_revision: Union[str, Sequence[str], None] = '944ebe8db918'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    op.execute(
        """
        UPDATE orders
        SET status = CASE status
            WHEN 'PENDING' THEN 'pending'
            WHEN 'PAID' THEN 'paid'
            WHEN 'FAILED' THEN 'canceled'
            WHEN 'CANCELLED' THEN 'canceled'
            ELSE status
        END
        """
    )
    with op.batch_alter_table(
        "order_items",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.drop_constraint(
            "unique_order_movie_constraint",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_order_items_movie_id_movies",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_order_items_order_id_orders",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_order_items_movie_id_movies",
            "movies",
            ["movie_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_order_items_order_id_orders",
            "orders",
            ["order_id"],
            ["id"],
        )
        batch_op.alter_column(
            "price_at_purchase",
            new_column_name="price_at_order",
            existing_type=sa.DECIMAL(precision=10, scale=2),
            existing_nullable=False,
        )

    with op.batch_alter_table(
        "orders",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.VARCHAR(length=9),
            type_=sa.Enum(
                "pending",
                "paid",
                "canceled",
                name="orderstatusenum",
                native_enum=False,
                length=50,
            ),
            existing_nullable=False,
        )
        batch_op.alter_column(
            "total_amount",
            existing_type=sa.DECIMAL(precision=10, scale=2),
            nullable=True,
        )
        batch_op.drop_constraint(
            "fk_orders_user_id_users",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_orders_user_id_users",
            "users",
            ["user_id"],
            ["id"],
        )
        batch_op.drop_column("updated_at")


def downgrade() -> None:
    """Downgrade schema."""
    naming_convention = {
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    op.execute(
        """
        UPDATE orders
        SET status = CASE status
            WHEN 'pending' THEN 'PENDING'
            WHEN 'paid' THEN 'PAID'
            WHEN 'canceled' THEN 'CANCELLED'
            ELSE status
        END
        """
    )
    with op.batch_alter_table(
        "orders",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(),
                server_default=sa.text("(CURRENT_TIMESTAMP)"),
                nullable=False,
            )
        )
        batch_op.drop_constraint(
            "fk_orders_user_id_users",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_orders_user_id_users",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.alter_column(
            "total_amount",
            existing_type=sa.DECIMAL(precision=10, scale=2),
            nullable=False,
        )
        batch_op.alter_column(
            "status",
            existing_type=sa.Enum(
                "pending",
                "paid",
                "canceled",
                name="orderstatusenum",
                native_enum=False,
                length=50,
            ),
            type_=sa.VARCHAR(length=9),
            existing_nullable=False,
        )

    with op.batch_alter_table(
        "order_items",
        naming_convention=naming_convention,
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_order_items_order_id_orders",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_order_items_movie_id_movies",
            type_="foreignkey",
        )
        batch_op.create_foreign_key(
            "fk_order_items_order_id_orders",
            "orders",
            ["order_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_foreign_key(
            "fk_order_items_movie_id_movies",
            "movies",
            ["movie_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.alter_column(
            "price_at_order",
            new_column_name="price_at_purchase",
            existing_type=sa.DECIMAL(precision=10, scale=2),
            existing_nullable=False,
        )
        batch_op.create_unique_constraint(
            "unique_order_movie_constraint",
            ["order_id", "movie_id"],
        )
