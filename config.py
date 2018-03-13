#!/usr/bin/env python
# Per-machine configuration: Loads setting from ~/.epidermal

import os
import ConfigParser

class Config:
    def __init__(self, config_filepath='~/.epidermal'):

        # Default configuration values
        self.debug_flask = 1

        # Database connection
        self.db_address = 'localhost'
        self.db_port = 27017

        # Admin page
        self.admin_username = 'admin'
        self.admin_password = 'password'

        # Storage path for image data (large)
        self.data_path = '/media/data_cifs/sven2/epidermal'

        # Storage for patches when retraining
        self.train_data_path = '/media/data/epidermal'
        self.caffe_path = '/home/sven2/s2caffe/build'
        self.caffe_train_baseweights = '/home/sven2/caffedata/bvlc_reference_caffenet.caffemodel'
        self.caffe_train_options = '--gpu 0'

        # Storage path for model weights (large)
        self.model_path = '/home/sven2/caffedata_cifs'

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
        self.plot_path = '/data2/epidermal/plots'

        # Local overloads
        if config_filepath is not None:
            self.load(config_filepath)

    def load(self, config_filepath):
        config_filepath = os.path.expanduser(config_filepath)
        if os.path.isfile(config_filepath):
            reader = ConfigParser.ConfigParser()
            reader.read(config_filepath)
            config_fields = self.get_fields()
            for f in config_fields:
                setattr(self, f, self.load_value(reader, f, getattr(self, f)))

    def get_fields(self, prefix=''):
        return [attr for attr in dir(self)
                if not callable(getattr(self, attr)) and not attr.startswith('__') and attr.startswith(prefix)]

    def load_value(self, reader, field_name, default_value):
        if reader.has_option('Epidermal', field_name):
            if isinstance(default_value, basestring):
                return reader.get('Epidermal', field_name)
            elif isinstance(default_value, int):
                return reader.getint('Epidermal', field_name)
            elif isinstance(default_value, list):
                assert(isinstance(default_value[0], basestring)) # Only lists of strings supported (comma-separated)
                s = reader.get('Epidermal', field_name)
                return s.split(',')
            else:
                raise RuntimeError('Invalid config type %s for value %s=%s.' % (type(default_value), field_name, str(default_value)))
        else:
            # No overload
            return default_value

    def print_values(self):
        for f in self.get_fields():
            print '%s = %s' % (f, getattr(self, f))

    def set_app_config(self, app):
        app.debug = (self.debug_flask > 0)
        app_fields = self.get_fields(prefix='APP_')
        for f in app_fields:
            app.config[f[4:]] = getattr(self, f)


config = Config()

if __name__ == '__main__':
    config.print_values()
