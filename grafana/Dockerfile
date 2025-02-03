FROM grafana/grafana:latest

# Set Grafana environment variables
ENV GF_SECURITY_ADMIN_USER=certaik \
    GF_SECURITY_ADMIN_PASSWORD=testing \
    GF_USERS_ALLOW_SIGN_UP=false

# Copy provisioning files from local directory
COPY provisioning /etc/grafana/provisioning/

# Create volume mount point for Grafana data
VOLUME ["/var/lib/grafana"]

# Expose Grafana port
EXPOSE 9000

# The entrypoint and cmd are inherited from the base image
