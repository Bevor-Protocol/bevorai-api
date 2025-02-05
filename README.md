# Certaik API

To be used for interfacing with certaik application, and main function is for managing the GAME api integration with Virtuals.

## Getting started

Install `poetry`

`poetry install` will create your virtual environment

`docker compose up` will start the services

### Redis

Redis queue is used for background processing, and to enable cron tasks.

### Migrations

Migrations are intentionally not run upon application startup. Since we have watcherfiles, I didn't want migrations to run that were potentially being edited.

To create a migration, run the following:

`poetry run aerich migrate --name [migration_name]`

To apply migrations, run:

`./scripts/run-migration.sh`

This will execute inside the API container.

### Auth seeder

To generate + test the authentication workflow in the frontend, you need to seed the database.

`poetry run python -m scripts.seeder`

this will output the generated raw API key in the console. Copy it and paste it into the frontend ENV file. This script generates a first-party application key, and allows you to interface with the API.

In the instance that you were SIWE on the frontend prior to generating the auth seed, you'll need to disconnect and re-authenticate. This will create your user observation in the DB, and now the frontend will be able to make API requests on behalf of your authenticated user.

### Poetry

All instances of needing to prefix a script with `poetry run ...` can be substituted out by entering the poetry shell `poetry shell`, then you can execute the commands without the prefix.