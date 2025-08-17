#!/bin/bash

export DEBUG=0
export PROCRASTINATE_APP="e2e.tasks.app"

pip install procrastinate==3.2.2

opal-procrastinate init-db

opal-procrastinate defer-jobs -i jobs.json

procrastinate worker -q default --one-shot

# this raises an error if tasks where not executed properly
anystore --store data get job1/next_task
anystore --store data get job2/next_task

# cancellation / status test
pytest -c pyproject.toml -s ./test_e2e.py

if [ $? -ne 0 ]; then
    rm -rf data
    exit 1
fi

rm -rf data
