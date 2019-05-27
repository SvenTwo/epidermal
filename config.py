#!/usr/bin/env python
# Per-machine configuration: Loads setting from ~/.epidermal

import os
import ConfigParser


def expand_path(path):
    path = os.path.expandvars(os.path.expanduser(path))
    if not os.path.isdir(path):
        print 'Creating data path', path
        os.makedirs(path)
    return path


class Config:
    SectionName = 'Epidermal'

    def __init__(self, config_filepath='~/.epidermal', save_missing=False):

        # Default configuration values
        self.debug_flask = False

        # Database connection
        self.db_address = 'localhost'
        self.db_port = 27017

        # Admin page
        self.admin_username = 'admin'
        self.admin_password = 'password'

        # Storage path for image data (large)
        self.data_path = '~/epidermal/data'

        # Storage for patches when retraining
        self.train_data_path = os.path.join(self.data_path, 'train')
        self.caffe_path = '~/caffe/build'
        self.caffe_train_baseweights = '~/epidermal/bvlc_reference_caffenet.caffemodel'
        self.caffe_train_options = '--gpu 0'

        # Storage path for model weights (large)
        self.model_path = os.path.join(self.data_path, 'models')

        self.server_path = os.path.join(self.data_path, 'server')
        self.server_image_path = os.path.join(self.server_path, 'images')
        self.server_heatmap_path = os.path.join(self.server_path, 'heatmaps')
        self.image_extensions = ['.jpg', '.jpeg', '.png']
        self.archive_extensions = ['.zip']
        self.max_image_file_size = 1024 * 1024 * 50 # 50MB
        self.worker_gpu_index = 0

        # Local source root
        self.src_path = os.path.dirname(__file__)

        # Flask app config
        self.APP_SECRET_KEY = ''  # Set this in .epidermal!
        self.APP_SECURITY_REGISTERABLE = True
        self.APP_SECURITY_CHANGEABLE = True
        self.APP_SECURITY_PASSWORD_SALT = ''  # Set this in .epidermal!
        self.APP_DEFAULT_MAIL_SENDER = 'stomatacounter@gmail.com'
        self.APP_SECURITY_EMAIL_SENDER = 'stomatacounter@gmail.com'
        self.APP_SECURITY_REGISTERABLE = True
        self.APP_SECURITY_CONFIRMABLE = False
        self.APP_SECURITY_RECOVERABLE = True

        self.APP_MAIL_SERVER = 'smtp.gmail.com'
        self.APP_MAIL_PORT = 465
        self.APP_MAIL_USE_SSL = True
        self.APP_MAIL_USERNAME = 'stomatacounter@gmail.com'
        self.APP_MAIL_PASSWORD = ''  # Set this in .epidermal!

        # MongoDB Config
        self.APP_MONGODB_DB = 'epidermal'
        self.APP_MONGODB_HOST = 'localhost'
        self.APP_MONGODB_PORT = 27017

        # For evaluation
        self.plot_path = os.path.join(self.data_path, 'plots')

        # Local overloads
        if config_filepath is not None:
            self.load(config_filepath, save_missing=save_missing)

    def get_data_path(self):
        return expand_path(self.data_path)

    def get_plot_path(self):
        return expand_path(self.plot_path)

    def get_model_path(self):
        return expand_path(self.model_path)

    def get_train_data_path(self):
        return expand_path(self.train_data_path)

    def get_caffe_path(self):
        return expand_path(self.caffe_path)

    def get_caffe_train_baseweights(self):
        return expand_path(self.caffe_train_baseweights)

    def get_server_path(self):
        return expand_path(self.server_path)

    def get_server_image_path(self):
        return expand_path(self.server_image_path)

    def get_server_heatmap_path(self):
        return expand_path(self.server_heatmap_path)

    def load(self, config_filepath, save_missing=False):
        config_filepath = os.path.expanduser(config_filepath)
        reader = ConfigParser.ConfigParser()
        reader.epi_config_has_changes = False
        if os.path.isfile(config_filepath):
            reader.read(config_filepath)
        config_fields = self.get_fields()
        for f in config_fields:
            setattr(self, f, self.load_value(reader, f, default_value=getattr(self, f), save_missing=save_missing))
        if reader.epi_config_has_changes:
            reader.write(open(config_filepath, 'wt'))
            print 'Default configuration values written to', config_filepath
        else:
            print 'Configuration loaded from', config_filepath

    def get_fields(self, prefix=''):
        return [attr for attr in dir(self)
                if not callable(getattr(self, attr)) and not attr.startswith('__') and attr.startswith(prefix)]

    def load_value(self, reader, field_name, default_value=None, save_missing=False):
        if reader.has_option(Config.SectionName, field_name):
            if isinstance(default_value, basestring):
                return reader.get(Config.SectionName, field_name)
            elif isinstance(default_value, bool):
                return reader.getboolean(Config.SectionName, field_name)
            elif isinstance(default_value, int):
                return reader.getint(Config.SectionName, field_name)
            elif isinstance(default_value, list):
                assert(isinstance(default_value[0], basestring)) # Only lists of strings supported (comma-separated)
                s = reader.get(Config.SectionName, field_name)
                return s.split(',')
            else:
                raise RuntimeError('Invalid config type %s for value %s=%s.' % (type(default_value), field_name, str(default_value)))
        elif save_missing:
            if not reader.has_section(Config.SectionName):
                reader.add_section(Config.SectionName)
            if isinstance(default_value, list):
                default_value = ','.join(default_value)
            reader.set(Config.SectionName, field_name, default_value)
            reader.epi_config_has_changes = True
        return default_value

    def print_values(self):
        for f in self.get_fields():
            print '%s = %s' % (f, getattr(self, f))

    def set_app_config(self, app):
        app.debug = self.debug_flask
        app_fields = self.get_fields(prefix='APP_')
        for f in app_fields:
            app.config[f[4:]] = getattr(self, f)


config = Config(save_missing=True)
