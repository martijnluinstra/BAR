from flask import Blueprint

bp = Blueprint('auction', __name__, url_prefix='/auction')

from . import views
