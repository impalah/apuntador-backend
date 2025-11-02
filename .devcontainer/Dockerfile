FROM mcr.microsoft.com/devcontainers/python:1-3.12-bullseye

# Instala uv y mueve el binario al PATH global
RUN curl -Ls https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/

# Instala AWS CLI v2 y jq, con detección automática de arquitectura
RUN apt-get update && \
    apt-get install -y unzip curl groff less jq && \
    ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        AWS_CLI_URL="https://awscli.amazonaws.com/awscli-exe-linux-aarch64.zip"; \
    else \
        echo "❌ Unsupported architecture: $ARCH" && exit 1; \
    fi && \
    curl "$AWS_CLI_URL" -o "awscliv2.zip" && \
    unzip awscliv2.zip && \
    ./aws/install && \
    rm -rf awscliv2.zip aws

# Establece el directorio de trabajo
WORKDIR /workspace

# Copia archivos para sincronizar dependencias
COPY pyproject.toml ./
COPY uv.lock* ./

# No se crea entorno ni instala nada aquí — eso lo hace el postCreateCommand
