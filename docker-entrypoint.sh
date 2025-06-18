#!/bin/bash

set -e

# initialize db
opal-procrastinate initdb

exec "$@"
