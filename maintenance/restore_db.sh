#!/usr/bin/env bash
# Dump epidermal DB for backup

mongorestore --drop --db epidermal_test /data2/epidermal/server/dump_test/epidermal_test
