"""add post_html base on markdown

Revision ID: 2d8ab89636e8
Revises: 195f6923682b
Create Date: 2016-07-13 16:51:19.564584

"""

# revision identifiers, used by Alembic.
revision = '2d8ab89636e8'
down_revision = '195f6923682b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('posts', sa.Column('body_html', sa.Text(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('posts', 'body_html')
    ### end Alembic commands ###
