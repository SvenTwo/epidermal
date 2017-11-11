# Hopkins statistic estimation
# https://matevzkunaver.wordpress.com/2017/06/20/hopkins-test-for-cluster-tendency/
# [1] Validating Clusters using the Hopkins Statistic from IEEE 2004.

from sklearn.neighbors import NearestNeighbors
from random import sample
from numpy.random import uniform
import numpy as np
from math import isnan
import pandas as pd

def hopkins(X):
    print 'Hopkins on shape ', X.shape
    X = pd.DataFrame(X)
    d = X.shape[1]
    # d = len(vars) # columns
    n = len(X)  # rows
    if not n:
        return 0.0
    m = int(0.1 * n)  # heuristic from article [1]
    nbrs = NearestNeighbors(n_neighbors=1).fit(X.values)
    rand_X = sample(range(0, n, 1), m)

    ujd = []
    wjd = []
    for j in range(0, m):
        u_dist, _ = nbrs.kneighbors(uniform(np.amin(X, axis=0), np.amax(X, axis=0), d).reshape(1, -1), 2,
                                    return_distance=True)
        ujd.append(u_dist[0][1])
        w_dist, _ = nbrs.kneighbors(X.iloc[rand_X[j]].values.reshape(1, -1), 2, return_distance=True)
        wjd.append(w_dist[0][1])

    eps = 1.0e-10
    H = (sum(ujd)+eps) / (sum(ujd) + sum(wjd) + eps)
    if isnan(H):
        print ujd, wjd
        H = 0

    return H