FROM alpine:3

RUN apk add 'py-spy=0.3.14-r0' --update-cache --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ --allow-untrusted

ENTRYPOINT ["py-spy"]
CMD ["--help"]
