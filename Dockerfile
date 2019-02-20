FROM ubuntu:18.04

# provide a build arg of UID to match the host during development
# useful for yielding files w/ correct perms to host fs from the container
ARG UID=1000

# recommended for python in docker
ENV PYTHONUNBUFFERED 1

# direct pipenv to make venv in project dir
ENV PIPENV_VENV_IN_PROJECT 1

# needed by pipenv to activate shell
ENV LANG en_US.UTF-8
ENV LC_ALL C.UTF-8
ENV SHELL /bin/bash

# django
RUN apt-get update \
    && apt-get install -y \
               python3-pip \
               postgresql-client \
               # -- start dev
               inotify-tools \
               # -- end dev
    && pip3 install --no-cache-dir --upgrade pip==18.0 pipenv \
    && useradd -lmU -u $UID user \
    && mkdir /app \
    && chown -R user:user /app

# create an unprivileged user to tie to running user
WORKDIR /app

# set user to user
USER user:user
