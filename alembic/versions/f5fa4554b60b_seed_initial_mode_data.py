"""Seed initial mode data

Revision ID: f5fa4554b60b
Revises: 06734005a296
Create Date: 2024-08-13 07:08:13.062102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5fa4554b60b'
down_revision: Union[str, None] = '06734005a296'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

schema = 'predictions'
table_name = 'mst_mode'

def upgrade() -> None:
    mst_mode=sa.Table(
        table_name,
        sa.MetaData(),
        sa.Column('idmode', sa.String, primary_key=True),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('value', sa.Integer, nullable=False),
        schema=schema
    )
    op.bulk_insert(mst_mode,
        [
            {"idmode":"MOD-0001","name":"WALKING","value":100},        
            {"idmode":"MOD-0002","name":"JOGGING","value":300},        
            {"idmode":"MOD-0003","name":"SPRINT","value":500},        
        ]
    )

def downgrade() -> None:
    op.execute(
         f'DELETE FROM {schema}.{table_name} WHERE idmode IN (\'MOD-0001\', \'MOD-0002\', \'MOD-0003\')'
    )
