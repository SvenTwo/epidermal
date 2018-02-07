#!/usr/bin/env python
# DB query tests

import db
from scipy.ndimage.morphology import generate_binary_structure, binary_erosion


# Test
if __name__ == '__main__':
    s = generate_binary_structure(2, 2)
    print s