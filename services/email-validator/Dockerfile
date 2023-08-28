FROM curlimages/curl AS entrypoint

ARG DUMB_INIT=https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64

USER root

RUN curl -sSfLo /usr/local/bin/dumb-init $DUMB_INIT && \
    chmod +x /usr/local/bin/dumb-init


FROM python:3.11-alpine

WORKDIR /app

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init

ENV PYTHONUNBUFFERED=1

COPY requirements*.txt /

RUN apk add --update gcc musl-dev linux-headers && \
    pip install -U pip -r /requirements.txt -r /requirements-tracing.txt && \
    rm -rf /requirements*.txt /root/.cache/

COPY . .

ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["/app/main.py"]
