#!/bin/bash

prefect work-pool create --type process batch --overwrite
prefect worker start -p batch &

python /main.py
