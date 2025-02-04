#!/bin/bash
set -e # Exit on error

echo "Running database migrations..."
poetry run aerich upgrade

echo "Running database seeder..."
poetry run python scripts/seeder.py

echo "Pre-deploy tasks completed successfully"