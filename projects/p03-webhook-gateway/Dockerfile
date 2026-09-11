# Pin: Go 1.24.0 on Alpine, matching platform/services/flaky-api.
FROM golang:1.24.0-alpine AS build

WORKDIR /src

COPY go.mod ./
COPY ingress ./ingress
COPY cmd ./cmd

RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/p03-ingress ./cmd/ingress

FROM alpine:3.21

RUN addgroup -S -g 1000 app \
    && adduser -S -u 1000 -G app -H -D app

COPY --from=build --chown=app:app /out/p03-ingress /usr/local/bin/p03-ingress

USER app

ENV P03_INGRESS_ADDR=:8103

EXPOSE 8103

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["p03-ingress", "-healthcheck"]

CMD ["p03-ingress"]
