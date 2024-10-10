FROM curlimages/curl AS entrypoint

ARG DUMB_INIT='https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64'

USER root
RUN curl -sSLo /usr/local/bin/dumb-init ${DUMB_INIT} && \
    chmod +x /usr/local/bin/dumb-init

FROM python:3.13-alpine

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init

RUN apk add --update build-base linux-headers && \
    pip install -U pip 'memory-profiler<1'

ENTRYPOINT ["dumb-init", "--"]
CMD ["mprof", "--help"]
