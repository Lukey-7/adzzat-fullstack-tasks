FROM debian:bookworm-slim

# GnuCOBOL builds the program; python3 is only for the grader and for the
# agent's convenience. No network access is needed after the build.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gnucobol3 python3 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY app/ /app/
