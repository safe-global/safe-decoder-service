FROM python:3.13-slim

EXPOSE 8888/tcp
ARG APP_HOME=/app
WORKDIR ${APP_HOME}
ENV PYTHONUNBUFFERED=1

COPY requirements-prod.txt ./requirements.txt
RUN set -ex \
	&& buildDeps=" \
		build-essential \
        curl \
		" \
    && apt-get update \
    && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends postgresql-client $buildDeps \
    && curl https://sh.rustup.rs -sSf | sh -s -- -y \
	&& export PATH="$PATH:$HOME/.cargo/bin" \
    && pip install -U --no-cache-dir wheel setuptools pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir ipython \
    && apt-get purge -y --auto-remove $buildDeps \
    && rm -rf /var/lib/apt/lists/* \
    && rustup self uninstall -y \
    && find /usr/local \
        \( -type d -a -name test -o -name tests \) \
        -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
        -exec rm -rf '{}' +


# /nginx mount point must be created before so it doesn't have root permissions
# ${APP_HOME} root folder will not be updated by COPY --chown, so permissions need to be adjusted
RUN groupadd -g 999 python && \
    useradd -u 999 -r -g python python && \
    mkdir -p /nginx && \
    chown -R python:python /nginx ${APP_HOME}
COPY --chown=python:python . .

# Use numeric ids so kubernetes identifies the user correctly
USER 999:999
