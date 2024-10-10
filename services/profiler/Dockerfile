FROM curlimages/curl AS entrypoint

ARG DUMB_INIT='https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64'

USER root
RUN curl -sSLo /usr/local/bin/dumb-init ${DUMB_INIT} && \
    chmod +x /usr/local/bin/dumb-init

FROM alpine:3 AS py-spy

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init

RUN apk add 'py-spy=0.3.14-r0' --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --allow-untrusted && which py-spy


FROM python:3.13-alpine

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init
COPY --from=py-spy /usr/bin/py-spy /usr/local/bin/py-spy

RUN apk add --update build-base linux-headers libunwind-dev && \
    pip install -U pip 'memory-profiler<1' 'honcho<2'

ENTRYPOINT ["dumb-init", "--"]
