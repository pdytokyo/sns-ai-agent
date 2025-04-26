"""Add competitor model

Revision ID: b125a22ba292
Revises: a125a22ba292
Create Date: 2025-04-26 19:55:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import sqlite


revision = 'b125a22ba292'
down_revision = 'a125a22ba292'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('competitor_videos',
    sa.Column('id', sa.Integer(), nullable=True),
    sa.Column('platform', sa.String(), nullable=False),
    sa.Column('video_url', sa.String(), nullable=False),
    sa.Column('engagement_rate', sa.Float(), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=True),
    sa.Column('like_count', sa.Integer(), nullable=True),
    sa.Column('comment_count', sa.Integer(), nullable=True),
    sa.Column('share_count', sa.Integer(), nullable=True),
    sa.Column('transcript', sa.String(), nullable=True),
    sa.Column('time_codes', sqlite.JSON(), nullable=False),
    sa.Column('char_counts', sqlite.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('competitor_videos')
