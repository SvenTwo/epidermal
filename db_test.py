#!/usr/bin/env python
# DB query tests

import db
from bson import ObjectId


# Test
if __name__ == '__main__':
    db.set_model_status(ObjectId('59177ddff2eebf18f8893bb3'), db.model_status_trained)
    db.set_model_parameters(ObjectId('5a72b711bca3b7043a0df395'), {'sample_limit': 10})
