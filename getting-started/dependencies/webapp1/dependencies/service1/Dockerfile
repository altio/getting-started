# always pin to an explicit tag, build up a base with all of the OS
# dependencies needed by deploy and dev
FROM ubuntu:bionic-20190807 as base

# install os dependencies needed for python, postgres client, and whatever else
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-pip \
        # provide db client from manage.py in container
        postgresql-client \
    # reduce the size of the saved layer
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/* \
    # install suitable versions of pip and pipenv for python env management
    && pip3 install --no-cache-dir --upgrade pip==18.0 pipenv

# recommended for python in docker
ENV PYTHONUNBUFFERED 1

# direct pipenv to make venv in project dir
ENV PIPENV_VENV_IN_PROJECT 1

# prevent log pollution
ENV PIPENV_NOSPIN 1

# needed by pipenv to activate shell
ENV LANG en_US.UTF-8
ENV LC_ALL C.UTF-8
ENV SHELL /bin/bash

# provide build args of UID and USER. Matching the host's UID during dev allows
# one to yield files to host fs w/ correct perms from the container
ARG UID=1000
ARG USER=user

# build args are only at build-time...need to set inside container
ENV UID=${UID}
ENV USER=${USER}

# setup OS environment
RUN echo "BASE IMAGE CREATED WITH ${USER} AS ${UID}" \
    && useradd -lmU -u ${UID} -s /bin/bash ${USER} \
    && mkdir /app \
    && chown -R ${USER}:${USER} /app

# set working directory to /app
WORKDIR /app

# create a layer for use by dev/build/test/doc/deploy
FROM base as dev

# install any additional OS dependencies required for dev/build/test/doc/deploy
RUN apt-get update && apt-get install -y --no-install-recommends \
        # django devserver file watch improvements
        inotify-tools \
        # needed to build psycopg2 -- could use psycopg2-binary but then you
        # are tied to their library versions and that could cause problems
        gcc \
        libpq-dev \
        python3-dev \
    # reduce the size of the saved layer
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN echo ${UID} ${USER}

# set container user to unprivileged user
# NOTE: this does not happen in base so root can install additional deps
USER ${USER}:${USER}

# create the build layer
FROM dev as build

# copy the file system in
COPY . /app

# install deploy dependencies and make a wheel
# NOTE: depending how you split things, you may need to --dev here
# fail immediately if lock os out of date
RUN pipenv install --deploy \
    # now install rest of dev (build) deps
    && pipenv install --dev \
    # generate the deploy requirements file
    && pipenv lock -r > requirements.txt \
    # generate the wheels for the deployment requirements
    && pipenv run pip wheel -r requirements.txt -w dist/

# finally, yield the deploy layer
FROM base as deploy

# copy over the wheel
COPY --from=build /app/dist /app/dist
COPY Pipfile* /app/

# forcibly install any bdist wheels (they have binary) then let install-deploy skip those
RUN pipenv run pip install dist/*.whl \
    && pipenv install --deploy \
    # && pip install *.whl \
    && rm -fr dist

USER $USER:$USER
