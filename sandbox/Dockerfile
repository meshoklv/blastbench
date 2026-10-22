# Sandbox image: a throwaway Linux box with PostgreSQL, Python and git.
# The agent under test gets a shell here and nothing else: no network, no host mounts.
FROM postgres:16-alpine

RUN apk add --no-cache bash coreutils findutils grep sed gawk diffutils patch git jq tar \
        python3 py3-pytest \
    && adduser -D -u 1000 -s /bin/bash agent \
    && mkdir -p /work /opt/sandbox

COPY exec_server.py entrypoint.sh /opt/sandbox/
RUN chmod 755 /opt/sandbox/entrypoint.sh

ENV PGDATA=/var/lib/postgresql/data
EXPOSE 8080
HEALTHCHECK --interval=2s --timeout=3s --retries=30 CMD wget -qO- http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["/opt/sandbox/entrypoint.sh"]
