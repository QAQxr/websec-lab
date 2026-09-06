#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

curl --fail --silent --show-error http://127.0.0.1:8080/health >/dev/null
curl --fail --silent --show-error http://127.0.0.1:8080/ | grep -q "AcmeCloud"

for port in 6379 8081; do
    if timeout 2 bash -c ": </dev/tcp/127.0.0.1/${port}" >/dev/null 2>&1; then
        echo "unexpected host port is open: ${port}" >&2
        exit 1
    fi
done

for service_port in "mysql 3306" "redis 6379" "internal-api 8081"; do
    service="${service_port% *}"
    port="${service_port##* }"
    published="$(docker compose port "${service}" "${port}")"
    if [ -n "${published}" ] && [ "${published}" != ":0" ]; then
        echo "unexpected published Compose port: ${service}:${port}" >&2
        exit 1
    fi
done

if timeout 2 bash -c ": </dev/tcp/127.0.0.1/3306" >/dev/null 2>&1; then
    echo "note: host port 3306 is occupied by an unrelated listener; this Compose project does not publish MySQL"
fi

for network in websec_lab_proxy_private websec_lab_app_private; do
    [ "$(docker network inspect "${network}" --format '{{.Internal}}')" = "true" ]
    [ "$(docker network inspect "${network}" --format '{{index .Options "com.docker.network.bridge.inhibit_ipv4"}}')" = "true" ]
done

[ "$(docker network inspect websec_lab_host_ingress --format '{{.Internal}}')" = "false" ]

if docker compose exec -T web python -c 'import urllib.request; urllib.request.urlopen("http://example.com", timeout=2)' >/dev/null 2>&1; then
    echo "web has unexpected public egress" >&2
    exit 1
fi

for service in web internal-api; do
    mounts="$(docker compose ps -q "${service}" | xargs docker inspect --format '{{range .Mounts}}{{.Source}}{{"\n"}}{{end}}')"
    if printf '%s\n' "${mounts}" | grep -Eq '(/var/run/docker.sock|/home/|/\.ssh/|/\.config/)'; then
        echo "sensitive host mount found in ${service}" >&2
        exit 1
    fi
done

echo "Phase 2.1 host and network checks passed."
