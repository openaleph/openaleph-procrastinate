#!/bin/bash

export DEBUG=0
export PROCRASTINATE_APP="e2e.tasks.app"
# export PROCRASTINATE_DB_URI="postgresql:///openaleph"

opal-procrastinate init-db

opal-procrastinate defer-jobs -i jobs.json

procrastinate worker -q default --one-shot

# this raises an error if tasks where not executed properly
anystore --store data get job1/next_task
anystore --store data get job2/next_task

if [ $? -ne 0 ]; then
    rm -rf data
    exit 1
fi

rm -rf data
