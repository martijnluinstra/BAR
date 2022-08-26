from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, validators


class AuctionForm(FlaskForm):
    description = StringField('Product description (optional)', validators=[
    	validators.Optional(strip_whitespace=True)
    ])
    price = IntegerField('Price (in Euro cent)', validators=[
    	validators.InputRequired(message='Price is required')
    ])
    participant = StringField('Participant', validators=[
    	validators.InputRequired(message='Participant is required')
    ])
