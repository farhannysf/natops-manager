ARG BASE_IMAGE=python
ARG BASE_TAG=3.12
FROM ${BASE_IMAGE}:${BASE_TAG}

ARG OS_USERNAME
RUN useradd -m -u 1000 ${OS_USERNAME}

WORKDIR /app
COPY requirements.txt .
COPY . .

RUN chown -R ${OS_USERNAME}: /app && \
    pip install --no-cache-dir -r requirements.txt && \
    chmod +x /app/entrypoint

ENTRYPOINT [ "./entrypoint" ]