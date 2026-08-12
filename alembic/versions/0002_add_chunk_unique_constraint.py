"""문서별 청크 인덱스 유일성 보장.

Revision ID: 0002
Revises: 0001
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM chunks
        WHERE id IN (
            SELECT id
            FROM (
                SELECT
                    id,
                    row_number() OVER (
                        PARTITION BY document_id, index
                        ORDER BY id
                    ) AS duplicate_rank
                FROM chunks
            ) AS ranked_chunks
            WHERE duplicate_rank > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_chunks_document_id_index",
        "chunks",
        ["document_id", "index"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_chunks_document_id_index", "chunks", type_="unique")
