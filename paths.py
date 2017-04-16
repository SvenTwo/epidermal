#!/usr/bin/env python
# Filesystem path settings

import os

# Storage path for model definitions (small)
run_path = '/home/sven2/s2caffe/runs/'

# Storage path for image data (large)
data_path = '/media/data_cifs/sven2/epidermal'

# Storage path for model weights (large)
model_path = '/home/sven2/caffedata_cifs'

server_path = os.path.join(data_path, 'server')
server_image_path = os.path.join(server_path, 'images')
server_heatmap_path = os.path.join(server_path, 'heatmaps')
image_extensions = ['.jpg', '.jpeg', '.png']
