#!/usr/bin/env bash
#
# wapiti / trailcam service group — project-plan §3.1/§9 (wificam §7.2.1
# pattern), landed by WI-103.
#
#   ./start-stop-services.sh --status
#   ./start-stop-services.sh --start  --service=trailcam-server
#   ./start-stop-services.sh --stop   --service=trailcam-server
#   ./start-stop-services.sh --start  --service=trailcam-builder   # one-shot
#
# Services:
#   trailcam-server   nginx + php-fpm app, host port **4444**
#                     (the 4430–4443 block is bound by other projects on this
#                     machine — port decided in the WI-101 plan review, §3.1;
#                     production keeps https://wapiti.cam)
#   trailcam-builder  one-shot composer/asset builder (builder/Dockerfile.builder)
#   trailcam-test     one-shot test runner             (builder/Dockerfile.test)
#   trailcam-sim      device simulator fleet           (WI-105 — sim/sim.py)
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PORT="${TRAILCAM_PORT:-4444}"
APP_IMAGE="trailcam-server:v1"
BUILDER_IMAGE="trailcam-builder:v1"
TEST_IMAGE="trailcam-test:v1"
SIM_IMAGE="trailcam-sim:v1"

ACTION=""
SERVICE="trailcam-server"
for arg in "$@"; do
    case "$arg" in
        --start)      ACTION="start" ;;
        --stop)       ACTION="stop" ;;
        --status)     ACTION="status" ;;
        --service=*)  SERVICE="${arg#--service=}" ;;
        -h|--help)    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown argument: $arg" >&2; exit 2 ;;
    esac
done

if [ -z "$ACTION" ]; then
    echo "usage: $0 --start|--stop|--status [--service=NAME]" >&2
    exit 2
fi

state_of() {   # RUNNING | STOPPED | ABSENT
    local st
    if st="$(docker inspect -f '{{.State.Status}}' "$1" 2>/dev/null)"; then
        [ "$st" = "running" ] && echo "RUNNING" || echo "$(echo "$st" | tr '[:lower:]' '[:upper:]')"
    else
        echo "ABSENT"
    fi
}

short_image_state() {   # READY | MISSING
    if docker image inspect "$1" >/dev/null 2>&1; then echo "READY"; else echo "MISSING"; fi
}

do_status() {
    echo "trailcam-server: $(state_of trailcam-server)  (port :${APP_PORT}, image ${APP_IMAGE})"
    echo "trailcam-builder: $(short_image_state "$BUILDER_IMAGE")  (one-shot, image ${BUILDER_IMAGE})"
    echo "trailcam-test: $(short_image_state "$TEST_IMAGE")  (one-shot, image ${TEST_IMAGE})"
    if [ -f "$REPO/sim/sim.py" ]; then
        echo "trailcam-sim: $(short_image_state "$SIM_IMAGE")  (one-shot, image ${SIM_IMAGE})"
    else
        echo "trailcam-sim: MISSING  (WI-105 — sim/sim.py not landed yet)"
    fi
}

start_one_shot() {   # $1 = service, $2 = image, $3 = run args…
    local name="$1" image="$2"; shift 2
    if ! docker image inspect "$image" >/dev/null 2>&1; then
        echo "$name: image $image not built yet" >&2
        return 1
    fi
    echo "$name: running one-shot…"
    docker run --rm -v "$REPO/server:/var/www/html" -v "$REPO:/repo" "$image" "$@"
}

do_start() {
    case "$SERVICE" in
        trailcam-server)
            if [ "$(state_of trailcam-server)" = "RUNNING" ]; then
                echo "trailcam-server: already RUNNING"
                return 0
            fi
            docker rm -f trailcam-server >/dev/null 2>&1 || true
            docker run -d --name trailcam-server \
                -p "${APP_PORT}:443" \
                -v "$REPO/server:/var/www/html" \
                "$APP_IMAGE" >/dev/null
            echo "trailcam-server: started on host :${APP_PORT} (migrate + nginx boot inside the container)"
            ;;
        trailcam-builder)
            start_one_shot trailcam-builder "$BUILDER_IMAGE" ;;
        trailcam-test)
            start_one_shot trailcam-test "$TEST_IMAGE" ;;
        trailcam-sim)
            start_one_shot trailcam-sim "$SIM_IMAGE" ;;
        *)
            echo "unknown service: $SERVICE" >&2
            return 2 ;;
    esac
}

do_stop() {
    case "$SERVICE" in
        trailcam-server)
            if [ "$(state_of trailcam-server)" = "ABSENT" ]; then
                echo "trailcam-server: already absent"
            else
                docker rm -f trailcam-server >/dev/null
                echo "trailcam-server: stopped"
            fi
            ;;
        trailcam-builder|trailcam-test|trailcam-sim)
            echo "$SERVICE: one-shot (nothing to stop)" ;;
        *)
            echo "unknown service: $SERVICE" >&2
            return 2 ;;
    esac
}

case "$ACTION" in
    status) do_status ;;
    start)  do_start ;;
    stop)   do_stop ;;
esac
