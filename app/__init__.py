import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security, SQLAlchemyUserDatastore
from flask_login import LoginManager


db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
security = Security()

def get_user_datastore():
    from app.models import User, Role
    return SQLAlchemyUserDatastore(db, User, Role)

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object('app.config')
    app.config.from_pyfile('config.py')  # Load the instance configuration

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    # login_manager.login_view = 'main.login_custom'  # The view to redirect to for login
    # login_manager.login_message = 'Successful login!'

    security.init_app(app, get_user_datastore())

    from app.views import bp
    app.register_blueprint(bp)

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

    return app


# User loader callback function
@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    return User.query.get(int(user_id))
