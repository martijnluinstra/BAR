import datetime

import flask_login as login

from bar import db


class Activity(db.Model, login.UserMixin):
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    passcode = db.Column(db.String(40), nullable=False, unique=True)
    active = db.Column(db.Boolean(), nullable=False, default=True)
    is_archived = db.Column(db.Boolean(), nullable=False, default=False)
    has_secretary_access = db.Column(db.Boolean(), nullable=False, default=False)
    archived_stats = db.Column(db.String(4096), nullable=True)
    # settings
    age_limit = db.Column(db.Integer, nullable=False, default=18)
    stacked_purchases = db.Column(db.Boolean(), nullable=False, default=True)
    require_terms = db.Column(db.Boolean(), nullable=False, default=False)
    terms = db.Column(db.String(4096), nullable=True)
    faq = db.Column(db.String(4096), nullable=True)
    uuid_prefix = db.Column(db.String(255), nullable=True)
    participants = db.relationship('Participant', backref='activity', lazy='dynamic')

    def is_active(self):
        return self.active

    def to_dict(self):
        settings_fields = ['age_limit', 'stacked_purchases', 'require_terms', 'terms', 'faq']
        settings = dict((field.name, getattr(self, field.name)) for field in self.__table__.columns if field.name in settings_fields)
        return {
            'id': self.id,
            'name': self.name,
            'passcode': self.passcode,
            'settings': settings,
            'participants': [p.to_dict() for p in self.participants.all()],
            'products': [p.to_dict() for p in self.products.all()],
            'pos_purchases': [p.to_dict() for p in self.pos_purchases.all()],
            'auction_purchases': [p.to_dict() for p in self.auction_purchases.all()] 
        }


class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cover_id = db.Column(db.Integer(), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    iban = db.Column(db.String(34), nullable=False)
    bic = db.Column(db.String(11), nullable=True)
    birthday = db.Column(db.DateTime(), nullable=True)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    has_agreed_to_terms = db.Column(db.Boolean(), nullable=False, default=False)
    barcode = db.Column(db.String(255), nullable=True)
    uuid = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('cover_id', 'activity_id'),
        db.UniqueConstraint('name', 'activity_id'),
        {'mysql_engine':'InnoDB'},
    )

    @property
    def age(self):
        # datetime.timedelta does not account for leap years
        # See https://stackoverflow.com/questions/2217488/age-from-birthdate-in-python
        if not self.birthday:
            return None
        today = datetime.date.today()
        return today.year - self.birthday.year - ((today.month, today.day) < (self.birthday.month, self.birthday.day))

    def to_dict(self):
        exclude = ['birthday']
        result = dict((field.name, getattr(self, field.name)) for field in self.__table__.columns if field.name not in exclude)
        result['birthday'] = self.birthday.isoformat() if self.birthday else None
        return result


class Purchase(db.Model):
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey('participant.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    timestamp = db.Column(db.DateTime(), nullable=False)
    undone = db.Column(db.Boolean(), default=False, nullable=False)

    participant = db.relationship('Participant', backref=db.backref('pos_purchases', lazy='dynamic'))
    activity = db.relationship('Activity', backref=db.backref('pos_purchases', lazy='dynamic'))
    product = db.relationship('Product')

    def __init__(self, **kwargs):
        self.timestamp = datetime.datetime.now()
        super(Purchase, self).__init__(**kwargs)

    def to_dict(self):
        exclude = ['timestamp']
        result = dict((field.name, getattr(self, field.name)) for field in self.__table__.columns if field.name not in exclude)
        result['timestamp'] = self.timestamp.isoformat()
        return result


class Product(db.Model):
    __table_args__ = {'mysql_engine':'InnoDB'}
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Integer(), nullable=False, default=1)
    activity_id = db.Column(db.Integer, db.ForeignKey('activity.id'), nullable=False)
    priority = db.Column(db.Integer(), nullable=False, default=0)
    age_limit = db.Column(db.Boolean(), nullable=False, default=False)

    activity = db.relationship('Activity', backref=db.backref('products', lazy='dynamic'))

    def to_dict(self):
        return dict((field.name, getattr(self, field.name)) for field in self.__table__.columns)
