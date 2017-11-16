#!/usr/bin/env python
# User dataset functions

from flask import render_template, Blueprint
from webapp_base import pop_last_error
from flask_mongoengine import MongoEngine
from flask_mail import Mail
from flask_security import Security, MongoEngineUserDatastore, \
    UserMixin, RoleMixin, current_user

user_datasets = Blueprint('user_datasets', __name__, template_folder='templates')

@user_datasets.route('/user_datasets')
def user_datasets_page():
    return render_template('user_datasets.html', datasets=[], enqueued=[], error=pop_last_error())


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

    # Setup {{ user }} template variable
    @app.context_processor
    def inject_content():
        return dict(user=current_user)
