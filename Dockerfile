# Amazon Linux 2023 base image (latest: 2023.7.20250331)
FROM amazonlinux:2023

# Install Python 3.13 and required system packages
RUN dnf update -y && \
    dnf install -y --allowerasing \
    python3.13 \
    python3.13-pip \
    python3.13-devel \
    gcc \
    gcc-c++ \
    make \
    postgresql-devel \
    shadow-utils \
    curl \
    nodejs \
    npm \
    && dnf clean all

# Create a non-root user
RUN useradd -m -u 65532 nonroot

# Set Python 3.13 as default
RUN alternatives --install /usr/bin/python3 python3 /usr/bin/python3.13 1 && \
    alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.13 1

# Install Phoenix and dependencies as root (latest version)
RUN pip3 install --no-cache-dir "arize-phoenix[container,pg]>=12.7.0"

# Create working directory
RUN mkdir -p /mnt/data && chown -R nonroot:nonroot /mnt/data

# Set environment variables
ENV PHOENIX_WORKING_DIR=/mnt/data
ENV PATH=/usr/local/bin:$PATH

# Switch to non-root user
USER nonroot
WORKDIR /home/nonroot

# Expose ports
EXPOSE 6006 4317 9090

# Run Phoenix server
CMD ["python3", "-m", "phoenix.server.main", "serve"]