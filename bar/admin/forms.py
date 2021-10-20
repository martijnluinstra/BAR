from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import TextField, BooleanField, validators

class ActivityForm(Form):
    name = TextField('Name', [validators.InputRequired(message='Name is required')])
    passcode = TextField('Passcode', [validators.InputRequired(message='Passcode is required')])
    active = BooleanField('Active')
    has_secretary_access = BooleanField('Has secretary access')

class ActivityConfirmForm(Form):
    name = TextField("Enter this activity's name to confirm.", [validators.InputRequired(message='Name is required')])

class ImportForm(Form):
    import_file = FileField('Activity JSON', validators=[
        FileRequired(), 
        FileAllowed(['json'], 'JSON files only!')
        ])
    name = TextField('Name (optional)', validators=[
        validators.Optional(strip_whitespace=True)
        ])
    passcode = TextField('Passcode', validators=[
        validators.Optional(strip_whitespace=True)
        ])
