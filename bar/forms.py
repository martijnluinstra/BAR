from flask.ext.wtf import Form
from flask.ext.wtf.file import FileField, FileAllowed, FileRequired
from wtforms import TextField, BooleanField, IntegerField, DateTimeField, RadioField, SelectField, validators

from models import Activity

class ActivityForm(Form):
    name = TextField('Name', [validators.InputRequired(message='Name is required')])
    passcode = TextField('Passcode', [validators.InputRequired(message='Passcode is required')])
    active = BooleanField('Active')
    
class ParticipantForm(Form):
    name = TextField('Name', [validators.InputRequired(message='Name is required')])
    address = TextField('Address', [validators.InputRequired(message='Address is required')])
    city = TextField('Place of residence', [validators.InputRequired(message='Place of residence is required')])
    email = TextField('Email address', [validators.InputRequired(message='Email is required'), validators.Email(message='Invalid email address')])
    iban = TextField('IBAN', [validators.InputRequired(message='IBAN is required'), validators.length(max=34, message='An IBAN may not be longer than 34 characters')])
    bic = TextField('BIC (optional)', [validators.Optional(strip_whitespace=True), validators.length(max=11, message='A BIC may not be longer than 11 characters')])
    birthday  = DateTimeField('Birthday (optional)', format='%d-%m-%Y', validators=[validators.Optional(strip_whitespace=True)])


class BirthdayForm(Form):
    name = TextField('Name', [validators.InputRequired(message='Name is required')])
    birthday  = DateTimeField('Birthday', format='%d-%m-%Y', validators=[validators.InputRequired(message='Birthday is required')])


class ProductForm(Form):
    name = TextField('Name', [validators.InputRequired(message='Name is required')])
    price = IntegerField('Price', [validators.InputRequired(message='Price is required')])
    priority = IntegerField('Priority (position of the button)', [validators.InputRequired(message='Priority is required')])
    age_limit = BooleanField('Age limit')


class ImportForm(Form):
    import_file = FileField('Participants CSV', validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    delimiter = SelectField('Delimiter', choices=[(';', ';'), (',', ',')])
    header = BooleanField('This file has a header')


class SettingsForm(Form):
    trade_credits = RadioField('Trading currency', choices=[('True','Credits'),('False','Euro')])
    credit_value = IntegerField('Credit value (in Euro cent)')
    age_limit = IntegerField('Age limit (minimal legal age)', [validators.InputRequired(message='Age limit is required')])
    stacked_purchases = BooleanField('Allow stacked purchases (e.g. buy 6 beers at once)')

    def validate_trade_credits(form, field):
        field.data = field.data == 'True'

    def validate_credit_value(form, field):
        if not form.trade_credits:
            return
        if not field.raw_data or not field.raw_data[0]:
            field.errors[:] = []
            raise validators.StopValidation('Credit value is requried!')
