from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import MetaData

from flask_coverapi import CoverSessionManager


naming_convention = {
    'ix': 'ix_%(column_0_label)s',
    'uq': 'uq_%(table_name)s_%(column_0_name)s',
    'ck': 'ck_%(table_name)s_%(column_0_name)s',
    'fk': 'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s',
    'pk': 'pk_%(table_name)s'
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
migrate = Migrate(compare_type=True)

csrf = CSRFProtect()

login_manager = LoginManager()
cover_session_manager = CoverSessionManager()


def create_app():
    # Init app
    app = Flask(__name__)
    app.config.from_object('config')

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    if not app.config.get('STAND_ALONE', False):
        cover_session_manager.init_app(app)

    login_manager.login_view = 'pos.login'

    from . import admin, auction, pos, utils
    app.register_blueprint(admin.bp)
    app.register_blueprint(auction.bp)
    app.register_blueprint(pos.bp)

    utils.init_app(app)

    from .pos.models import Activity

    @login_manager.user_loader
    def load_activity(activity_id):
        return Activity.query.get(activity_id)

    return app
