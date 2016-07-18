"""add focus

Revision ID: 0d2b4bc8b80b
Revises: bf8ab1a614e7
Create Date: 2016-07-16 01:46:34.775554

"""

# revision identifiers, used by Alembic.
revision = '0d2b4bc8b80b'
down_revision = 'bf8ab1a614e7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('focus',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('post_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['post_id'], ['posts.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('focus')
    ### end Alembic commands ###
