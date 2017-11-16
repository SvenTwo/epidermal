import os
from flask import render_template, request, Response, Blueprint
from config import config


users = Blueprint('users', __name__, template_folder='templates')

