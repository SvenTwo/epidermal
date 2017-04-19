#!/usr/bin/env python
# Per-machine configuration: Loads setting from ~/.epidermal

import os
import ConfigParser

class Config:
    def __init__(self, config_filepath='~/.epidermal'):

        # Default configuration values

        # Database connection
        self.db_address = 'localhost'
        self.db_port = 27017

        # Storage path for model definitions (small)
        self.run_path = '/home/sven2/s2caffe/runs/'

        # Storage path for image data (large)
        self.data_path = '/media/data_cifs/sven2/epidermal'

        # Storage path for model weights (large)
        self.model_path = '/home/sven2/caffedata_cifs'

        self.server_path = os.path.join(self.data_path, 'server')
        self.server_image_path = os.path.join(self.server_path, 'images')
        self.server_heatmap_path = os.path.join(self.server_path, 'heatmaps')
        self.image_extensions = ['.jpg', '.jpeg', '.png']


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

    def get_fields(self):
        return [attr for attr in dir(self) if not callable(getattr(self, attr)) and not attr.startswith('__')]

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

config = Config()

if __name__ == '__main__':
    config.print_values()
