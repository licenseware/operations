FROM curlimages/curl AS entrypoint

ARG DUMB_INIT=https://github.com/Yelp/dumb-init/releases/download/v1.2.5/dumb-init_1.2.5_x86_64

USER root

RUN curl -sSfLo /usr/local/bin/dumb-init $DUMB_INIT && \
    chmod +x /usr/local/bin/dumb-init


FROM python:3.11-alpine

WORKDIR /app

COPY --from=entrypoint /usr/local/bin/dumb-init /usr/local/bin/dumb-init

COPY requirements.txt .

RUN pip install -Ur requirements.txt pip

COPY . .

ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD ["python", "main.py"]
