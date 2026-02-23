"""create alimentos, ejercicios, metas_usuario

Revision ID: 004_nutricion
Revises: e7f8g9h0i1j2
Create Date: 2026-02-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '004_nutricion'
down_revision: Union[str, Sequence[str], None] = 'e7f8g9h0i1j2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'alimentos',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('nombre_normalizado', sa.String(255), nullable=False),
        sa.Column('marca', sa.String(255), nullable=True),
        sa.Column('origen', sa.String(64), nullable=True),
        sa.Column('calorias', sa.Float(), nullable=False),
        sa.Column('proteinas_g', sa.Float(), nullable=False),
        sa.Column('carbohidratos_g', sa.Float(), nullable=False),
        sa.Column('grasas_g', sa.Float(), nullable=False),
        sa.Column('fibra_g', sa.Float(), nullable=True),
        sa.Column('azucares_g', sa.Float(), nullable=True),
        sa.Column('grasas_saturadas_g', sa.Float(), nullable=True),
        sa.Column('sodio_mg', sa.Float(), nullable=True),
        sa.Column('colesterol_mg', sa.Float(), nullable=True),
        sa.Column('calcio_mg', sa.Float(), nullable=True),
        sa.Column('hierro_mg', sa.Float(), nullable=True),
        sa.Column('vitamina_c_mg', sa.Float(), nullable=True),
        sa.Column('vitamina_d_ug', sa.Float(), nullable=True),
        sa.Column('potasio_mg', sa.Float(), nullable=True),
        sa.Column('es_estimado', sa.Boolean(), default=False),
        sa.Column('porcion_por_defecto_g', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_alimentos_nombre', 'alimentos', ['nombre'])
    op.create_index('ix_alimentos_nombre_normalizado', 'alimentos', ['nombre_normalizado'])

    op.create_table(
        'ejercicios',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('nombre', sa.String(255), nullable=False),
        sa.Column('nombre_normalizado', sa.String(255), nullable=False),
        sa.Column('alias', sa.Text(), nullable=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('met', sa.Float(), nullable=False),
        sa.Column('grupo_muscular', sa.String(128), nullable=True),
        sa.Column('origen', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ejercicios_nombre', 'ejercicios', ['nombre'])
    op.create_index('ix_ejercicios_nombre_normalizado', 'ejercicios', ['nombre_normalizado'])

    op.create_table(
        'metas_usuario',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('genero', sa.String(1), nullable=False),
        sa.Column('edad', sa.Integer(), nullable=False),
        sa.Column('peso_kg', sa.Float(), nullable=False),
        sa.Column('talla_cm', sa.Float(), nullable=False),
        sa.Column('nivel_actividad', sa.String(32), nullable=False),
        sa.Column('objetivo', sa.String(64), nullable=False),
        sa.Column('tmb', sa.Float(), nullable=False),
        sa.Column('get', sa.Float(), nullable=False),
        sa.Column('calorias_objetivo', sa.Float(), nullable=False),
        sa.Column('proteinas_g', sa.Float(), nullable=False),
        sa.Column('carbohidratos_g', sa.Float(), nullable=False),
        sa.Column('grasas_g', sa.Float(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_metas_usuario_client_id', 'metas_usuario', ['client_id'])


def downgrade() -> None:
    op.drop_index('ix_metas_usuario_client_id', 'metas_usuario')
    op.drop_table('metas_usuario')
    op.drop_index('ix_ejercicios_nombre_normalizado', 'ejercicios')
    op.drop_index('ix_ejercicios_nombre', 'ejercicios')
    op.drop_table('ejercicios')
    op.drop_index('ix_alimentos_nombre_normalizado', 'alimentos')
    op.drop_index('ix_alimentos_nombre', 'alimentos')
    op.drop_table('alimentos')
