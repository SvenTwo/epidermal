#!/usr/bin/env python
# Export-to-csv functionality

import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def get_plot_as_png():
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    return buf
