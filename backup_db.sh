#!/usr/bin/env bash

FN=$(date +%Y-%m-%d-%H-%M-%S)
mongodump -d epidermal -o "/data/epidermal_${FN}"
