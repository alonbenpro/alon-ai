#!/bin/sh
# Private, loopback-only L05 operator stack. Run from any directory.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)
# Compose gives exported variables precedence over --env-file. Only the validated
# private file may provide these values to the local stack.
unset ALON_AI_OPERATOR_PASSWORD_HASH ALON_AI_SESSION_SIGNING_KEY
AUTH_FILE=${ALON_AI_LOCAL_AUTH_FILE:-$ROOT/.local/operator.env}
case "$AUTH_FILE" in
    /*) ;;
    *) AUTH_FILE="$ROOT/$AUTH_FILE" ;;
esac
COMPOSE_FILE="$ROOT/infra/compose.yaml"
cd "$ROOT"

usage() {
    cat <<'EOF'
Usage: scripts/local-dev.sh {up|down|status|help}
  up      Start database, migrate, provision the operator, and start the app
  down    Stop the stack while keeping the database volume and login material
  status  Show container status
  help    Show this help
EOF
}

fail() {
    printf 'local-dev: %s\n' "$*" >&2
    exit 1
}

init_compose_project() {
    if [ -z "${COMPOSE_PROJECT_NAME:-}" ]; then
        command -v python3 >/dev/null 2>&1 || fail 'Python 3 is required to identify this checkout.'
        COMPOSE_PROJECT_NAME=$(python3 - "$ROOT" <<'PY'
import hashlib
import sys

print("alon-ai-" + hashlib.sha256(sys.argv[1].encode()).hexdigest()[:12])
PY
)
    fi
    export COMPOSE_PROJECT_NAME
}

docker_preflight() {
    command -v docker >/dev/null 2>&1 || fail 'Docker CLI is missing.'
    case "${COMPOSE:-docker compose}" in
        'docker compose') docker compose version >/dev/null 2>&1 || fail 'Docker Compose plugin is unavailable. Set COMPOSE=docker-compose if using the standalone CLI.' ;;
        docker-compose) command -v docker-compose >/dev/null 2>&1 && docker-compose version >/dev/null 2>&1 || fail 'Standalone docker-compose is unavailable.' ;;
        *) fail 'COMPOSE must be either "docker compose" or "docker-compose".' ;;
    esac
    docker info >/dev/null 2>&1 || fail 'Docker engine is unavailable. Start Docker Desktop or your selected engine.'
}

compose_cli() {
    if [ "${COMPOSE:-docker compose}" = docker-compose ]; then
        docker-compose "$@"
    else
        docker compose "$@"
    fi
}

compose() {
    if [ -f "$AUTH_FILE" ]; then
        compose_cli --env-file .env.example --env-file "$AUTH_FILE" -f "$COMPOSE_FILE" "$@"
    else
        compose_cli --env-file .env.example -f "$COMPOSE_FILE" "$@"
    fi
}

check_ports() {
    postgres_port=${ALON_AI_POSTGRES_PORT:-5432}
    api_port=${ALON_AI_API_PORT:-8000}
    frontend_port=${ALON_AI_FRONTEND_PORT:-3000}
    running=$(compose ps --status running --services)
    python3 - "$postgres_port" "$api_port" "$frontend_port" "$running" <<'PY'
import socket
import errno
import shutil
import subprocess
import sys

port_values = sys.argv[1:4]
running_text = sys.argv[4]
for label, value in zip(("ALON_AI_POSTGRES_PORT", "ALON_AI_API_PORT", "ALON_AI_FRONTEND_PORT"), port_values):
    if not value.isdecimal() or not 1 <= int(value) <= 65535:
        raise SystemExit(f"local-dev: {label} must be a TCP port from 1 to 65535")
if len(set(map(int, port_values))) != 3:
    raise SystemExit("local-dev: PostgreSQL, API, and frontend host ports must be distinct")
running = set(running_text.splitlines())
for service, port in zip(("postgres", "api", "frontend"), map(int, port_values)):
    if service in running:
        continue
    with socket.socket() as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind(("127.0.0.1", port))
        except OSError as error:
            if error.errno == errno.EPERM:
                if shutil.which("lsof") is None:
                    raise SystemExit("local-dev: cannot inspect local ports; install lsof or allow socket preflight") from None
                probe_result = subprocess.run(
                    ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                    capture_output=True, text=True, check=False,
                )
                if probe_result.returncode == 1 and not probe_result.stdout:
                    continue
                if probe_result.returncode not in (0, 1):
                    raise SystemExit(f"local-dev: cannot inspect port {port} with lsof") from None
            raise SystemExit(
                f"local-dev: port {port} is occupied; free it"
                + f" or set ALON_AI_{service.upper()}_PORT"
            ) from None
PY
}

guard_first_run_volume() {
    if [ -e "$AUTH_FILE" ] || [ -L "$AUTH_FILE" ]; then
        return
    fi
    config_json=$(compose config --format json) || fail 'Cannot inspect Compose configuration before first-run setup.'
    volume_name=$(printf '%s' "$config_json" | python3 -c 'import json,sys; print(json.load(sys.stdin)["volumes"]["postgres_data"]["name"])') || fail 'Cannot identify the PostgreSQL volume.'
    existing=$(docker volume ls --format '{{.Name}}' --filter "name=$volume_name") || fail 'Cannot inspect Docker volumes before first-run setup.'
    if printf '%s\n' "$existing" | grep -Fx "$volume_name" >/dev/null; then
        fail 'PostgreSQL data already exists without its local verifier. Restore the original private file or follow an explicit credential rotation procedure.'
    fi
}

prepare_auth() {
    python3 - "$AUTH_FILE" <<'PY'
import hashlib
import os
import re
import secrets
import stat
import sys
import termios
from pathlib import Path

target = Path(sys.argv[1])
parent = target.parent
if parent.is_symlink():
    raise SystemExit("local-dev: local configuration directory must not be a symlink")
parent.mkdir(mode=0o700, exist_ok=True)
if stat.S_IMODE(parent.stat().st_mode) != 0o700 or parent.stat().st_uid != os.getuid():
    raise SystemExit("local-dev: local configuration directory needs owner-only permissions (chmod 700 .local)")
if target.is_symlink():
    raise SystemExit("local-dev: operator configuration must not be a symlink")
if target.exists():
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid():
        raise SystemExit("local-dev: operator configuration needs owner-only permissions (chmod 600 .local/operator.env)")
    lines = target.read_text().splitlines()
    if len(lines) != 2 or not re.fullmatch(r"ALON_AI_OPERATOR_PASSWORD_HASH='scrypt\$16384\$8\$1\$[0-9a-f]{32}\$[0-9a-f]{64}'", lines[0]) or not re.fullmatch(r"ALON_AI_SESSION_SIGNING_KEY='[0-9a-f]{64}'", lines[1]):
        raise SystemExit("local-dev: operator configuration is malformed; inspect it privately before retrying")
    print("Reusing existing private operator configuration.")
    raise SystemExit(0)
try:
    terminal_in = os.open("/dev/tty", os.O_RDONLY)
    original = termios.tcgetattr(terminal_in)
except (OSError, termios.error):
    raise SystemExit("local-dev: first run needs a terminal that can suppress password echo") from None

def read_secret(prompt: str) -> str:
    hidden = original.copy()
    hidden[3] &= ~termios.ECHO
    changed = False
    try:
        try:
            termios.tcsetattr(terminal_in, termios.TCSAFLUSH, hidden)
            changed = True
        except termios.error:
            raise SystemExit("local-dev: terminal cannot suppress password echo") from None
        sys.stderr.write(prompt)
        sys.stderr.flush()
        buffer = bytearray()
        while True:
            character = os.read(terminal_in, 1)
            if not character:
                raise SystemExit("local-dev: terminal closed during password entry")
            if character in (b"\n", b"\r"):
                break
            buffer.extend(character)
            if len(buffer) > 4096:
                raise SystemExit("local-dev: password input is too long")
        return buffer.decode()
    finally:
        if changed:
            termios.tcsetattr(terminal_in, termios.TCSADRAIN, original)
            sys.stderr.write("\n")
            sys.stderr.flush()

try:
    password = read_secret("Create local operator password: ")
    confirmation = read_secret("Confirm local operator password: ")
finally:
    os.close(terminal_in)
if password != confirmation:
    raise SystemExit("local-dev: passwords did not match")
if not 12 <= len(password) <= 1024:
    raise SystemExit("local-dev: password must be 12 to 1024 characters")
salt = secrets.token_bytes(16)
derived = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32, maxmem=64 * 1024 * 1024)
verifier = f"scrypt$16384$8$1${salt.hex()}${derived.hex()}"
key = secrets.token_hex(32)
content = f"ALON_AI_OPERATOR_PASSWORD_HASH='{verifier}'\nALON_AI_SESSION_SIGNING_KEY='{key}'\n"
flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
descriptor = os.open(target, flags, 0o600)
with os.fdopen(descriptor, "w") as output:
    output.write(content)
print("Created private local operator configuration.")
PY
}

case "${1:-help}" in
    help|-h|--help)
        usage
        ;;
    up)
        [ "$#" -eq 1 ] || fail 'Usage: scripts/local-dev.sh up'
        init_compose_project
        command -v python3 >/dev/null 2>&1 || fail 'Python 3 is required for secure local setup.'
        command -v curl >/dev/null 2>&1 || fail 'curl is required for readiness checks.'
        docker_preflight
        check_ports
        guard_first_run_volume
        prepare_auth
        compose config --quiet || fail 'Compose configuration is invalid.'
        compose up -d --wait postgres || fail 'PostgreSQL failed to become healthy. Inspect docker compose logs postgres.'
        compose build api worker frontend || fail 'Application image build failed.'
        compose run --rm --no-deps api alembic upgrade head || fail 'Database migration failed; application services were not started.'
        compose run --rm --no-deps -v "$ROOT/scripts/provision_operator.py:/tmp/provision_operator.py:ro" api python /tmp/provision_operator.py || fail 'Operator provisioning failed. Existing operator data was left intact.'
        compose run --rm --no-deps worker dbos migrate --sys-db-url postgresql://alon_ai:alon_ai@postgres:5432/alon_ai --schema dbos || fail 'DBOS migration failed; application services were not started.'
        compose up -d --wait api worker frontend || fail 'Application services did not become ready. Inspect docker compose logs.'
        compose ps --status running --services worker | grep -Fx worker >/dev/null || fail 'Worker exited after startup. Inspect worker logs.'
        curl --fail --silent --show-error "http://127.0.0.1:$api_port/health/ready" >/dev/null || fail 'API readiness failed.'
        curl --fail --silent --show-error "http://127.0.0.1:$frontend_port/login" >/dev/null || fail 'Frontend login readiness failed.'
        printf 'Sign in: http://localhost:%s/login\nUse your local operator password. Manage the stack with scripts/local-dev.sh status or down.\n' "$frontend_port"
        ;;
    down)
        [ "$#" -eq 1 ] || fail 'Usage: scripts/local-dev.sh down'
        init_compose_project
        docker_preflight
        compose down
        printf 'Stack stopped; PostgreSQL data and local login material retained.\n'
        ;;
    status)
        [ "$#" -eq 1 ] || fail 'Usage: scripts/local-dev.sh status'
        init_compose_project
        docker_preflight
        compose ps
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac
