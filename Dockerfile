# Amazon Linux 2023 base image
FROM amazonlinux:2023

# Install Python 3.11 and required system packages
RUN dnf update -y && \
    dnf install -y --allowerasing \
    python3.11 \
    python3.11-pip \
    python3.11-devel \
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

# Set Python 3.11 as default
RUN alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1

# Install Phoenix and dependencies as root
RUN pip3 install --no-cache-dir "arize-phoenix[container,pg]"

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