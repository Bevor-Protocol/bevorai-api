#!/usr/bin/env python3
import subprocess
import sys


def main():
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", "name=api"],
            capture_output=True,
            text=True,
            check=True,
        )

        if result.stdout.strip():
            print("Running migrations inside the 'api' container...")
            subprocess.run(
                ["docker", "exec", "-it", "api", "poetry", "run", "aerich", "upgrade"],
                check=True,
            )
        else:
            print("The 'api' container is not running. Please start it first.")
            return 1

        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
