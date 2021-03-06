"""empty message

Revision ID: 659029851f0a
Revises: 251bd70371aa
Create Date: 2019-09-06 00:46:57.090000

"""

# revision identifiers, used by Alembic.
revision = '659029851f0a'
down_revision = '251bd70371aa'

from alembic import op
import sqlalchemy as sa


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('activity', sa.Column('uuid_prefix', sa.String(length=255), nullable=True))
    op.create_foreign_key(None, 'auction_purchase', 'participant', ['participant_id'], ['id'])
    op.create_foreign_key(None, 'auction_purchase', 'activity', ['activity_id'], ['id'])
    op.add_column('participant', sa.Column('uuid', sa.String(length=255), nullable=True))
    op.create_foreign_key(None, 'participant', 'activity', ['activity_id'], ['id'])
    op.create_foreign_key(None, 'product', 'activity', ['activity_id'], ['id'])
    op.create_foreign_key(None, 'purchase', 'product', ['product_id'], ['id'])
    op.create_foreign_key(None, 'purchase', 'participant', ['participant_id'], ['id'])
    op.create_foreign_key(None, 'purchase', 'activity', ['activity_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'purchase', type_='foreignkey')
    op.drop_constraint(None, 'purchase', type_='foreignkey')
    op.drop_constraint(None, 'purchase', type_='foreignkey')
    op.drop_constraint(None, 'product', type_='foreignkey')
    op.drop_constraint(None, 'participant', type_='foreignkey')
    op.drop_column('participant', 'uuid')
    op.drop_constraint(None, 'auction_purchase', type_='foreignkey')
    op.drop_constraint(None, 'auction_purchase', type_='foreignkey')
    op.drop_column('activity', 'uuid_prefix')
    # ### end Alembic commands ###
