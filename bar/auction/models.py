from datetime import datetime

from bar import db


class AuctionPurchase(db.Model):
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer(), nullable=False)
    timestamp = db.Column(db.DateTime(), nullable=False)
    undone = db.Column(db.Boolean(), default=False, nullable=False)

    participant = db.relationship('Participant', backref=db.backref('auction_purchases', lazy='dynamic'))
    activity = db.relationship('Activity', backref=db.backref('auction_purchases', lazy='dynamic'))

    def __init__(self, **kwargs):
        self.timestamp = datetime.now()
        super(AuctionPurchase, self).__init__(**kwargs)

    def to_dict(self):
        exclude = ['timestamp']
        result = dict((field.name, getattr(self, field.name)) for field in self.__table__.columns if field.name not in exclude)
        result['timestamp'] = self.timestamp.isoformat()
        return result
