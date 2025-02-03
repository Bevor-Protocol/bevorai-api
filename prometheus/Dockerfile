FROM prom/prometheus:latest

# Set environment variables from Railway
ENV API_URL=${API_URL} \
    WORKER_URL=${WORKER_URL}

# Copy prometheus configuration file
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Expose Prometheus port
EXPOSE 9090

# Set the command to run Prometheus with the config file
CMD ["--config.file=/etc/prometheus/prometheus.yml"]
