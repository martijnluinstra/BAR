from flask import Blueprint

bp = Blueprint('pos', __name__, url_prefix='')

from . import views
