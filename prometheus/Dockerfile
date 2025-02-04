FROM prom/prometheus:latest

ARG API_URL
ARG WORKER_URL

# Copy prometheus configuration file
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Create and set volume for persistent data
VOLUME /prometheus

# Expose Prometheus port
EXPOSE 9090

# Set the command to run Prometheus with the config file
CMD ["--config.file=/etc/prometheus/prometheus.yml"]
