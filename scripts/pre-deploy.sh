#!/bin/bash
set -e # Exit on error

echo "Running database migrations..."
uv run aerich upgrade

echo "Running database seeder..."
uv run python scripts/seeder.py

echo "Pre-deploy tasks completed successfully"
