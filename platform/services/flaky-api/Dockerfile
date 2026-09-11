# Image tags looked up 2026-09-11 from Docker Hub (index digests).
FROM golang:1.24.0-alpine@sha256:2d40d4fc278dad38be0777d5e2a88a2c6dee51b0b29c97a764fc6c6a11ca893c AS builder

WORKDIR /src
ENV CGO_ENABLED=0

COPY go.mod ./
COPY *.go ./
RUN go build -trimpath -ldflags="-s -w" -o /out/flaky-api .

FROM alpine:3.21.3@sha256:a8560b36e8b8210634f77d9f7f9efd7ffa463e380b75e2e74aff4511df3ef88c

RUN addgroup -S -g 65532 app \
    && adduser -S -u 65532 -G app -H -D app

COPY --from=builder --chown=app:app /out/flaky-api /usr/local/bin/flaky-api

USER app
ENV FLAKY_API_ADDR=:8091
EXPOSE 8091

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/flaky-api", "-healthcheck"]

ENTRYPOINT ["/usr/local/bin/flaky-api"]
