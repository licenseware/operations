FROM curlimages/curl AS entrypoint

ARG DUMB_INIT='https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64'

USER root
RUN curl -sSLo /usr/local/bin/dumb-init ${DUMB_INIT} && \
    chmod +x /usr/local/bin/dumb-init

FROM alpine:3

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init

RUN apk add 'py-spy=0.3.14-r0' --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --allow-untrusted

ENTRYPOINT ["dumb-init", "--"]
CMD ["py-spy", "--help"]
