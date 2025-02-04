FROM prom/prometheus:latest

ARG API_URL
ARG WORKER_URL

# Copy prometheus configuration file
COPY prometheus.yml /etc/prometheus/prometheus.yml

# Railway doesn't support volumes through dockerfiles.

# Expose Prometheus port
EXPOSE 9090

# Set the command to run Prometheus with the config file
USER root
ENTRYPOINT [ "/bin/prometheus"]
CMD        [ "--config.file=/etc/prometheus/prometheus.yml", \
             "--storage.tsdb.path=/prometheus", \
             "--log.level=debug"]
