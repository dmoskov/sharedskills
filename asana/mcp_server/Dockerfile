# Build from the asana/ directory so the lib is in the context:
#   docker build -f mcp_server/Dockerfile -t asana-mcp .
FROM python:3.13-slim

WORKDIR /app
COPY mcp_server/requirements.txt mcp_server/requirements.txt
RUN pip install --no-cache-dir -r mcp_server/requirements.txt

COPY asana_client.py asana_to_markdown.py markdown_to_asana.py ./
COPY asana_sdk/ asana_sdk/
COPY mcp_server/asana_auth.py mcp_server/server.py mcp_server/

RUN useradd --system --uid 10001 app && mkdir -p /data && chown app /data
USER app

# FASTMCP_HOME holds the encrypted OAuth state (client registrations, users' Asana tokens).
# Mount persistent storage here or everyone has to reconnect after each deploy.
ENV FASTMCP_HOME=/data PORT=8000 PYTHONUNBUFFERED=1
VOLUME /data
EXPOSE 8000

CMD ["python", "mcp_server/server.py"]
