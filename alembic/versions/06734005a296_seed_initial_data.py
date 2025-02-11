"""Seed initial data

Revision ID: 06734005a296
Revises: 
Create Date: 2024-08-13 07:02:28.514211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.    
revision: str = '06734005a296'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


schema = 'predictions'
table_name = 'mst_alat'

def upgrade():
    # Define the table structure within the specified schema
    mst_alat = sa.Table(
        table_name,
        sa.MetaData(),
        sa.Column('idalat', sa.String, primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('mac_address', sa.String, nullable=False),
        sa.Column('type', sa.String, nullable=False),
        schema=schema
    )

    # Insert the initial data
    op.bulk_insert(mst_alat,
        [
            {"idalat": "ALT001", "name": "TX01A7K9L1", "mac_address": "EC:64:C9:85:37:08", "type": "tx"},
            {"idalat": "ALT002", "name": "RX01F8U7N1", "mac_address": "08:D1:F9:34:A4:1C", "type": "rx"}
        ]
    )

def downgrade():
    # Remove the inserted data on downgrade
    op.execute(
        f'DELETE FROM {schema}.{table_name} WHERE idalat IN (\'ALT001\', \'ALT002\')'
    )
