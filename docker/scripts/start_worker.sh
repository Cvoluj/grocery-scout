#!/bin/bash
taskiq worker src.tasks:broker src.email.tasks --workers ${WORKER_COUNT:-4}
