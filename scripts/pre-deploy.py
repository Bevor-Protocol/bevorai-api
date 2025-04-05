#!/usr/bin/env python3
import subprocess
import sys


def pre_deploy():
    try:
        print("Running database migrations...")
        subprocess.run(["uv", "run", "aerich", "upgrade"], check=True)

        print("Running database seeder...")
        subprocess.run(["uv", "run", "python", "scripts/seeder.py"], check=True)

        print("Pre-deploy tasks completed successfully")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error during pre-deploy: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(pre_deploy())
