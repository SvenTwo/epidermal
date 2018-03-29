#!/usr/bin/env python
# DB query tests

import db
from bson import ObjectId


# Test
if __name__ == '__main__':
    db.delete_model(db.get_model_by_name('cuticle_train')['_id'])
