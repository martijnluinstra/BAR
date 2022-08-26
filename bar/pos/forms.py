from flask import current_app
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, BooleanField, IntegerField, DateTimeField, RadioField, SelectField, validators, TextAreaField

from bar.utils import validate_bic, validate_iban


class ExportForm(FlaskForm):
    pos = BooleanField('Consumptions')
    auction = BooleanField('Auction')
    description_pos_prefix = StringField('Consumption description prefix (optional)', [validators.Optional(strip_whitespace=True)])
    description_auction_prefix = StringField('Auction description prefix (optional)', [validators.Optional(strip_whitespace=True)])
    description = StringField('Description (optional)', [validators.Optional(strip_whitespace=True)])


class ParticipantForm(FlaskForm):
    name = StringField('Name', validators=[
        validators.InputRequired(message='Name is required')
    ])
    member_id = IntegerField('Member ID', validators=[
        validators.Optional(strip_whitespace=True)
    ])
    address = StringField('Address', [
        validators.InputRequired(message='Address is required')
    ])
    city = StringField('Place of residence', [
        validators.InputRequired(message='Place of residence is required')
    ])
    email = StringField('Email address', [
        validators.InputRequired(message='Email is required'),
        validators.Email(message='Invalid email address')
    ])
    iban = StringField('IBAN', [
        validators.InputRequired(message='IBAN is required')
    ])
    bic = StringField('BIC (optional)', [
        validators.Optional(strip_whitespace=True),
        validators.length(max=11, message='A BIC may not be longer than 11 characters')
    ])
    birthday  = DateTimeField('Date of birth (optional)', format='%Y-%m-%d', validators=[
        validators.Optional(strip_whitespace=True)
    ])
    barcode = StringField('Barcode', [
        validators.Optional(strip_whitespace=True),
        validators.length(max=255)
    ])

    def validate_iban(form, field):
        try:
            validate_iban(field.data)
        except Exception as e:
            raise validators.ValidationError(str(e))

    def validate_bic(form, field):
        try:
            validate_bic(field.data)
        except Exception as e:
            raise validators.ValidationError(str(e))


class RegistrationForm(FlaskForm):
    name = StringField('Name', [validators.InputRequired(message='Name is required')])
    birthday = DateTimeField('Birthday', format='%d-%m-%Y', validators=[
        validators.Optional(strip_whitespace=True)
    ])
    barcode = StringField('Barcode', [
        validators.Optional(strip_whitespace=True),
        validators.length(max=255)
    ])


class ProductForm(FlaskForm):
    name = StringField('Name', [validators.InputRequired(message='Name is required')])
    price = IntegerField('Price (in Euro cent)', [validators.InputRequired(message='Price is required')])
    priority = IntegerField('Priority (position of the button)', [validators.InputRequired(message='Priority is required')])
    age_limit = BooleanField('Age limit')


class ImportForm(FlaskForm):
    import_file = FileField('Participants CSV', validators=[FileRequired(), FileAllowed(['csv'], 'CSV files only!')])
    delimiter = SelectField('Delimiter', choices=[(';', ';'), (',', ',')])
    header = BooleanField('This file has a header')


class SettingsForm(FlaskForm):
    age_limit = IntegerField('Age limit (minimal legal age)', [validators.InputRequired(message='Age limit is required')])
    stacked_purchases = BooleanField('Allow stacked purchases (e.g. buy 6 beers at once)')
    require_terms = BooleanField('Accept terms before purchases')
    terms = TextAreaField('Terms', [validators.length(max=4096)])
    faq = TextAreaField('FAQ', [
        validators.Optional(strip_whitespace=True),
        validators.length(max=4096)
    ])
    uuid_prefix = StringField('UUID Prefix', [validators.length(max=255)])

    def validate_terms(form, field):
        if not form.require_terms.data:
            return
        if not field.raw_data or not field.raw_data[0]:
            field.errors[:] = []
            raise validators.StopValidation('Terms are required!')
