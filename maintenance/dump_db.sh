#!/usr/bin/env bash
# Dump epidermal DB for backup

mongodump --db epidermal --out /data2/epidermal/server/dump
mongodump --db epidermal_test --out /data2/epidermal/server/dump_test