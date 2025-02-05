if [ "$(docker ps -q -f name=api)" ]; then
    echo "Running migrations inside the 'api' container..."
    # Execute the migration command inside the 'api' container
    docker exec -it api poetry run aerich upgrade
else
    echo "The 'api' container is not running. Please start it first."
fi