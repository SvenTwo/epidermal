#!/usr/bin/env bash
# Start webapp on test data

source ~/.virtualenvs/cv/bin/activate
python2.7 ../webapp.py --config ./test_config.cfg
