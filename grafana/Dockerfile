FROM grafana/grafana:latest

ARG GF_SECURITY_ADMIN_USER
ARG GF_SECURITY_ADMIN_PASSWORD
ARG GF_USERS_ALLOW_SIGN_UP

# Copy provisioning files from local directory
COPY provisioning /etc/grafana/provisioning/

# Create volume mount point for Grafana data
VOLUME ["/var/lib/grafana"]

# Expose Grafana port
EXPOSE 9000

# The entrypoint and cmd are inherited from the base image
