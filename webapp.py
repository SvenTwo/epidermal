#!/usr/bin/env python
# Stomata identification server: Main app

from flask import Flask, render_template
from config import config
from webapp_base import base as app_base
from webapp_admin import admin
from webapp_export import data_export
from webapp_users import users, setup_user
from webapp_user_datasets import user_datasets
from webapp_examples import examples
from webapp_annotations import annotations
from webapp_datasets import datasets
from webapp_samples import samples
from webapp_model import bp_model


app = Flask(__name__)
config.set_app_config(app)

if config.maintenance_text:
    print 'MAINTENANCE MODE:', config.maintenance_text
    @app.route('/', defaults={'path': ''})
    @app.route('/<path:path>')
    def catch_all(path):
        return render_template("maintenance.html", maintenance_text=config.maintenance_text, user={})
else:
    app.register_blueprint(admin)
    app.register_blueprint(app_base)
    app.register_blueprint(data_export)
    app.register_blueprint(users)
    app.register_blueprint(user_datasets)
    app.register_blueprint(examples)
    app.register_blueprint(annotations)
    app.register_blueprint(datasets)
    app.register_blueprint(samples)
    app.register_blueprint(bp_model)

    setup_user(app)


# Start flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8995)
