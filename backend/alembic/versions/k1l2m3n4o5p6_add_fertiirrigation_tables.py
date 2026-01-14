"""add fertiirrigation tables

Revision ID: k1l2m3n4o5p6
Revises: bc5d202224ff
Create Date: 2024-12-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, None] = 'bc5d202224ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('my_soil_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('laboratory', sa.String(length=100), nullable=True),
        sa.Column('analysis_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('texture', sa.String(length=50), nullable=True),
        sa.Column('bulk_density', sa.Float(), nullable=True),
        sa.Column('depth_cm', sa.Float(), nullable=True),
        sa.Column('ph', sa.Float(), nullable=True),
        sa.Column('ec_ds_m', sa.Float(), nullable=True),
        sa.Column('organic_matter_pct', sa.Float(), nullable=True),
        sa.Column('n_total_pct', sa.Float(), nullable=True),
        sa.Column('n_no3_ppm', sa.Float(), nullable=True),
        sa.Column('n_nh4_ppm', sa.Float(), nullable=True),
        sa.Column('p_ppm', sa.Float(), nullable=True),
        sa.Column('k_ppm', sa.Float(), nullable=True),
        sa.Column('ca_ppm', sa.Float(), nullable=True),
        sa.Column('mg_ppm', sa.Float(), nullable=True),
        sa.Column('s_ppm', sa.Float(), nullable=True),
        sa.Column('na_ppm', sa.Float(), nullable=True),
        sa.Column('cic_cmol_kg', sa.Float(), nullable=True),
        sa.Column('ca_exch', sa.Float(), nullable=True),
        sa.Column('mg_exch', sa.Float(), nullable=True),
        sa.Column('k_exch', sa.Float(), nullable=True),
        sa.Column('na_exch', sa.Float(), nullable=True),
        sa.Column('fe_ppm', sa.Float(), nullable=True),
        sa.Column('mn_ppm', sa.Float(), nullable=True),
        sa.Column('zn_ppm', sa.Float(), nullable=True),
        sa.Column('cu_ppm', sa.Float(), nullable=True),
        sa.Column('b_ppm', sa.Float(), nullable=True),
        sa.Column('caco3_pct', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_my_soil_analyses_id'), 'my_soil_analyses', ['id'], unique=False)
    op.create_index(op.f('ix_my_soil_analyses_user_id'), 'my_soil_analyses', ['user_id'], unique=False)
    
    op.create_table('fertiirrigation_calculations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('soil_analysis_id', sa.Integer(), nullable=True),
        sa.Column('water_analysis_id', sa.Integer(), nullable=True),
        sa.Column('crop_name', sa.String(length=100), nullable=False),
        sa.Column('crop_variety', sa.String(length=100), nullable=True),
        sa.Column('growth_stage', sa.String(length=50), nullable=True),
        sa.Column('irrigation_system', sa.String(length=50), nullable=True),
        sa.Column('irrigation_frequency_days', sa.Float(), nullable=True),
        sa.Column('irrigation_volume_m3_ha', sa.Float(), nullable=True),
        sa.Column('area_ha', sa.Float(), nullable=True),
        sa.Column('yield_target_ton_ha', sa.Float(), nullable=True),
        sa.Column('input_data', sa.JSON(), nullable=True),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('fertilizer_program', sa.JSON(), nullable=True),
        sa.Column('warnings', sa.JSON(), nullable=True),
        sa.Column('total_n_kg_ha', sa.Float(), nullable=True),
        sa.Column('total_p2o5_kg_ha', sa.Float(), nullable=True),
        sa.Column('total_k2o_kg_ha', sa.Float(), nullable=True),
        sa.Column('total_cost_estimate', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['soil_analysis_id'], ['my_soil_analyses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['water_analysis_id'], ['water_analyses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fertiirrigation_calculations_id'), 'fertiirrigation_calculations', ['id'], unique=False)
    op.create_index(op.f('ix_fertiirrigation_calculations_user_id'), 'fertiirrigation_calculations', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_fertiirrigation_calculations_user_id'), table_name='fertiirrigation_calculations')
    op.drop_index(op.f('ix_fertiirrigation_calculations_id'), table_name='fertiirrigation_calculations')
    op.drop_table('fertiirrigation_calculations')
    op.drop_index(op.f('ix_my_soil_analyses_user_id'), table_name='my_soil_analyses')
    op.drop_index(op.f('ix_my_soil_analyses_id'), table_name='my_soil_analyses')
    op.drop_table('my_soil_analyses')
