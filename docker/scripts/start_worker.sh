#!/bin/bash
taskiq worker src.tasks:broker --workers ${WORKER_COUNT:-4}
