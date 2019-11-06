FROM node:13.0.1 as dev

# provide build args of UID. Matching the host's UID during dev allows
# container to yield files with correct permissions
ARG UID=1000

# build args are only at build-time...need to set inside container
ENV UID=${UID}

# setup OS environment for node user
RUN echo "BASE IMAGE CREATED WITH ${USER} AS ${UID}" \
    && usermod -u ${UID} node \
    && groupmod -g ${UID} node

USER node:node

# set working directory to /app
WORKDIR /app
