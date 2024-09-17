FROM ubuntu:24.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    pipx \
    curl \
    build-essential \
    dictionaries-common \
    &&  \
    rm -rf /var/lib/apt/lists/* \
    && \
    pipx install poetry \
    && \
    pipx ensurepath

# create /app directory
WORKDIR /app
RUN cd /app

# copy the poetry configuration \
COPY pyproject.toml poetry.lock ./

# build the poetry environment
RUN bash -l -c "poetry install --no-root" \
    && \
    bash -l -c "poetry run playwright install"

# copy the python api code
COPY alea_web_survey alea_web_survey
COPY resources resources
COPY scripts scripts
COPY tests tests
COPY config.json config.json

RUN mkdir -p /root/.alea/web-survey \
    && \
    bash -l -c "poetry run python3 scripts/generate_domain_trie.py"

CMD ["bash", "-l", "-c", "PYTHONPATH=. poetry run python3 alea_web_survey/cli.py collect --push_every 100"]
