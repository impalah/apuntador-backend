FROM python:3.14 AS requirements-stage

ARG package_name=apuntador
ARG module_name=apuntador

# Create structure
WORKDIR /tmp
RUN mkdir projects

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv ~/.local/bin/uv /usr/local/bin/
RUN uv --version

# Generate requirements txt
COPY pyproject.toml uv.lock README.md ./projects/${package_name}/
RUN cd projects/${package_name} && uv export --no-emit-project --no-hashes --frozen --no-dev --no-editable -o requirements.txt

# ---------------------------------

# Build execution container
FROM python:3.14-alpine

# ARGs are needed in all the stages
ARG package_name=apuntador
ARG module_name=apuntador

# Install additional libraries
RUN apk add --no-cache gcc musl-dev curl-dev

# Create a non-root user and group
RUN addgroup -S appgroup && adduser -S appuser -G appgroup


ENV PORT=8000

EXPOSE 8000/tcp
EXPOSE 80/tcp

WORKDIR /app

# Install requirements
COPY --from=requirements-stage /tmp/projects/${package_name}/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./src /app

# Change ownership of the /app directory to the non-root user
RUN chown -R appuser:appgroup /app

# Switch to the non-root user
USER appuser


CMD ["sh", "-c", "uvicorn apuntador.main:app --host 0.0.0.0 --port $PORT"]
