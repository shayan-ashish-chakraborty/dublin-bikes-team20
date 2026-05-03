#!/bin/bash


SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
PROJECT_DIR=$(dirname "$(dirname "$SCRIPT_DIR")")

export PYTHONPATH=$PROJECT_DIR

cd $PROJECT_DIR

mkdir -p logs

nohup python sprint1_webscrappers/webscrapping_ec2/current_weather.py > logs/current_weather.log 2>&1 &
echo "current_weather.py activated, PID: $!"

nohup python sprint1_webscrappers/webscrapping_ec2/hourly_weather.py > logs/hourly_weather.log 2>&1 &
echo "hourly_weather.py activated, PID: $!"

nohup python sprint1_webscrappers/webscrapping_ec2/jcdecaux.py > logs/jcdecaux.log 2>&1 &
echo "jcdecaux.py activated, PID: $!"

echo "all tasks activated!"
