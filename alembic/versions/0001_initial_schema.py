"""Начальная схема: пользователи, бренды, категории, автомобили, запчасти.

Revision ID: 0001
Revises: 
Create Date: 2026-11-11 02:32:47.159558
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('brands',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('country', sa.String(length=100), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brands'))
    )
    with op.batch_alter_table('brands', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_brands_name'), ['name'], unique=True)

    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('name', name=op.f('uq_categories_name'))
    )
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_categories_slug'), ['slug'], unique=True)

    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('full_name', sa.String(length=255), nullable=True),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users'))
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)

    op.create_table('vehicles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('make', sa.String(length=100), nullable=False),
    sa.Column('model', sa.String(length=100), nullable=False),
    sa.Column('year_from', sa.Integer(), nullable=False),
    sa.Column('year_to', sa.Integer(), nullable=False),
    sa.Column('engine', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('year_from <= year_to', name=op.f('ck_vehicles_year_range')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_vehicles'))
    )
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_vehicles_make'), ['make'], unique=False)

    op.create_table('parts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('sku', sa.String(length=64), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('brand_id', sa.Integer(), nullable=False),
    sa.Column('category_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    sa.CheckConstraint('price >= 0', name=op.f('ck_parts_price_non_negative')),
    sa.CheckConstraint('quantity >= 0', name=op.f('ck_parts_quantity_non_negative')),
    sa.ForeignKeyConstraint(['brand_id'], ['brands.id'], name=op.f('fk_parts_brand_id_brands'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['category_id'], ['categories.id'], name=op.f('fk_parts_category_id_categories'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_parts'))
    )
    with op.batch_alter_table('parts', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_parts_brand_id'), ['brand_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_parts_category_id'), ['category_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_parts_name'), ['name'], unique=False)
        batch_op.create_index(batch_op.f('ix_parts_sku'), ['sku'], unique=True)

    op.create_table('part_vehicle',
    sa.Column('part_id', sa.Integer(), nullable=False),
    sa.Column('vehicle_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['part_id'], ['parts.id'], name=op.f('fk_part_vehicle_part_id_parts'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['vehicle_id'], ['vehicles.id'], name=op.f('fk_part_vehicle_vehicle_id_vehicles'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('part_id', 'vehicle_id', name=op.f('pk_part_vehicle'))
    )


def downgrade() -> None:
    op.drop_table('part_vehicle')
    with op.batch_alter_table('parts', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_parts_sku'))
        batch_op.drop_index(batch_op.f('ix_parts_name'))
        batch_op.drop_index(batch_op.f('ix_parts_category_id'))
        batch_op.drop_index(batch_op.f('ix_parts_brand_id'))

    op.drop_table('parts')
    with op.batch_alter_table('vehicles', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_vehicles_make'))

    op.drop_table('vehicles')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
    with op.batch_alter_table('categories', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_categories_slug'))

    op.drop_table('categories')
    with op.batch_alter_table('brands', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_brands_name'))

    op.drop_table('brands')
