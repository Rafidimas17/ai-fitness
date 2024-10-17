"""Add age column to mst_sesi

Revision ID: f6afd3865be5
Revises: f5fa4554b60b
Create Date: 2024-08-13 07:25:46.247910
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'f6afd3865be5'
down_revision: Union[str, None] = 'f5fa4554b60b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

schema = 'predictions'
table_name = 'mst_sesi'

def upgrade():
    # Add the 'age' column to the 'mst_sesi' table
    op.add_column(table_name, sa.Column('age', sa.Integer(), nullable=True), schema=schema)

def downgrade():
    # Remove the 'age' column from the 'mst_sesi' table
    op.drop_column(table_name, 'age', schema=schema)
