from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, BooleanField, validators


class ActivityForm(FlaskForm):
    name = StringField('Name', [validators.InputRequired(message='Name is required')])
    passcode = StringField('Passcode', [validators.InputRequired(message='Passcode is required')])
    active = BooleanField('Active')
    has_secretary_access = BooleanField('Has secretary access')


class ActivityConfirmForm(FlaskForm):
    name = StringField("Enter this activity's name to confirm.", [validators.InputRequired(message='Name is required')])


class ImportForm(FlaskForm):
    import_file = FileField('Activity JSON', validators=[
        FileRequired(), 
        FileAllowed(['json'], 'JSON files only!')
        ])
    name = StringField('Name (optional)', validators=[
        validators.Optional(strip_whitespace=True)
        ])
    passcode = StringField('Passcode', validators=[
        validators.Optional(strip_whitespace=True)
        ])
