#!/usr/bin/env python
# User functions

from flask import Blueprint
from flask_mongoengine import MongoEngine
from flask_mail import Mail
from flask_security import Security, MongoEngineUserDatastore, \
    UserMixin, RoleMixin, current_user


users = Blueprint('users', __name__, template_folder='templates')


# Get current user ID or 'None' if not logged in
def get_current_user_id():
    return None if (current_user is None) or (current_user.is_anonymous) else current_user.id


# App init user setup
def setup_user(app):
    mail = Mail(app)

    # Create database connection object
    db_engine = MongoEngine(app)

    class Role(db_engine.Document, RoleMixin):
        name = db_engine.StringField(max_length=80, unique=True)
        description = db_engine.StringField(max_length=255)

    class User(db_engine.Document, UserMixin):
        email = db_engine.StringField(max_length=255)
        password = db_engine.StringField(max_length=255)
        active = db_engine.BooleanField(default=True)
        confirmed_at = db_engine.DateTimeField()
        roles = db_engine.ListField(db_engine.ReferenceField(Role), default=[])

    # Setup Flask-Security
    user_datastore = MongoEngineUserDatastore(db_engine, User, Role)
    security = Security(app, user_datastore)
    app.config['SECURITY_POST_LOGIN_VIEW'] = '/user_datasets'

    # Setup {{ user }} template variable
    @app.context_processor
    def inject_content():
        return dict(user=current_user)
