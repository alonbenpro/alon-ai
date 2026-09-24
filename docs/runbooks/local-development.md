# Local operator development

This is the private L05 login and operator shell. Run from the repository root. The launcher reuses `infra/compose.yaml`, keeps all published ports on loopback, and leaves outreach and provider calls disabled.

## Prerequisites

- A running Docker engine and either the `docker compose` plugin or standalone `docker-compose` CLI.
- Python 3 with `hashlib.scrypt` and `curl` on the host. The application itself runs in containers; host `uv` and Node are needed only for host development and tests.
- Free loopback ports 3000, 8000, and 5432, or set `ALON_AI_FRONTEND_PORT`, `ALON_AI_API_PORT`, and `ALON_AI_POSTGRES_PORT` to three distinct free ports before `up`.

On macOS, Docker Desktop or Colima can provide the engine. With Colima and the Homebrew standalone Compose CLI:

```sh
colima start
export COMPOSE=docker-compose
```

Keep these variables in the same terminal for all launcher commands. If using Docker Desktop with its Compose plugin, no override is needed.

## Start and stop

```sh
make local-help
make local-up
make local-status
make local-down
```

`make local-up` checks Docker and local ports, then prompts for a password twice on the first run without echoing it. Choose a unique password of 12 to 1024 characters. The launcher stores **only** its scrypt verifier and a random session signing key in `.local/operator.env`; the file has mode `0600`, its directory has mode `0700`, and both are ignored by Git. It reuses this file on later runs. If the Compose project's PostgreSQL volume already exists but the verifier file is missing, startup refuses to create replacement credentials. Do not put the plaintext password or provider credentials in the file.

The launcher starts PostgreSQL, applies Alembic migrations, runs the existing idempotent single-operator provisioner, applies the DBOS schema, then starts the API, worker, and frontend. It waits for container health and checks the API and frontend over loopback. Open the printed sign-in URL (default <http://localhost:3000/login>) and use the password you created. The local subject is `local-operator@alon.ai`, and the provisioner displays the operator as `Alon`. Exported `ALON_AI_OPERATOR_PASSWORD_HASH` and `ALON_AI_SESSION_SIGNING_KEY` are ignored by the launcher; the validated private file supplies them to Compose.

The provisioner refuses a disabled operator or an already active operator with a different subject. It does not replace that row. Resolve that state deliberately; do not delete the PostgreSQL volume to bypass it. If the local verifier file is lost while the database remains, `up` refuses to generate a replacement. Restore it from a secure backup or use an explicit, separately reviewed credential rotation procedure.

`make local-down` stops containers and retains the PostgreSQL volume and `.local/operator.env`. It does not use `--volumes`. The commands are also available directly as `./scripts/local-dev.sh up|down|status|help`. By default, the launcher derives a stable Compose project name from this checkout's physical path, so another checkout uses different containers and a different PostgreSQL volume. Set `COMPOSE_PROJECT_NAME` explicitly to select a project; use the same value for every lifecycle command.

Stacks started before this checkout-specific default may still belong to their earlier Compose project. Inspect their project label before stopping them; the new default deliberately leaves their containers and PostgreSQL volume alone.

For an isolated, disposable verification run, set `COMPOSE_PROJECT_NAME=l05_disposable` and `ALON_AI_LOCAL_AUTH_FILE=/path/to/private/directory/operator.env` for **every** lifecycle command. The private directory must be owned by you and mode `0700`; the file is created with mode `0600`. Set `ALON_AI_POSTGRES_PORT`, `ALON_AI_API_PORT`, and `ALON_AI_FRONTEND_PORT` if their defaults are occupied. Keep these port values set for `up`, `status`, and `down` so Compose targets the same test stack. The project name gives the test stack its own PostgreSQL volume, while the auth-file override keeps the normal local verifier untouched. Ordinary `down` still retains this isolated volume; remove it only through a separately reviewed test cleanup after confirming the exact project and volume name.

## Manual L05 checks

1. Visit the URL printed by `up` in a fresh private browser window (or `http://localhost:${ALON_AI_FRONTEND_PORT:-3000}` for the root page). The login page should appear, and the shell should not display protected status before login.
2. Check the private status and readiness endpoints using the same port overrides as `up`:

   ```sh
   api_url="http://127.0.0.1:${ALON_AI_API_PORT:-8000}"
   frontend_url="http://127.0.0.1:${ALON_AI_FRONTEND_PORT:-3000}"
   curl -i "$api_url/operator/status" # 401 before login
   curl --fail "$api_url/health/live"
   curl --fail "$api_url/health/ready"
   curl --fail "$frontend_url/login"
   ```

3. Try a wrong password, then sign in with the local password. Confirm the shell shows real system status and activity (including empty or unknown states), not invented progress.
4. Refresh the page and open the status and activity surfaces. Confirm keyboard navigation, command search, focus, labels, and reduced-motion behavior at a desktop width of at least 1280px. A fresh stack may show an empty activity state; when a real server activity entry exists, open its read-only drawer and check keyboard focus and sanitized fields.
5. Log out. Browser back/refresh and the API's private endpoints should no longer expose prior operator data. Sign in again, then `make local-down`, `make local-up`, and confirm the original password still works.
6. For a failure drill, stop PostgreSQL via Compose and refresh status. The UI should show an unavailable state rather than retaining a healthy claim; restore with `make local-up`.

Do not paste login cookies, verifier, signing key, or passwords into bug reports or logs. This local stack uses example database credentials and HTTP on loopback. It is not a public deployment.

## Development and verification

The repository's existing `make setup`, `make generate`, `make lint`, `make typecheck`, `make test`, `make build`, and `make test-integration` targets remain available. `make dev` is the earlier general Compose path; use `make local-up` for a provisioned L05 login. Direct host API/worker development needs `ALON_AI_DATABASE_URL`, `ALON_AI_DBOS_SYSTEM_DATABASE_URL`, `ALON_AI_OPERATOR_AUTH_SUBJECT`, `ALON_AI_OPERATOR_PASSWORD_HASH`, and `ALON_AI_SESSION_SIGNING_KEY` set privately, plus the configured host port. Do not source `.local/operator.env` into a shared shell or print it while debugging.

Focused launcher check (no Docker engine needed):

```sh
python3 -m unittest scripts.tests.test_local_dev -v
sh -n scripts/local-dev.sh
docker-compose --env-file .env.example -f infra/compose.yaml config --quiet
```

Use `docker compose` in the last command when the plugin is installed. `make test-integration` requires a real PostgreSQL URL on the host and does not run as part of the launcher.

## Diagnosing failures

- **Docker unavailable:** run `docker info`; start Docker Desktop or the selected Colima profile, and set `COMPOSE=docker-compose` if only the standalone CLI is installed.
- **Port occupied:** set the matching `ALON_AI_FRONTEND_PORT`, `ALON_AI_API_PORT`, or `ALON_AI_POSTGRES_PORT` to a distinct free loopback port. Container-internal ports remain 3000, 8000, and 5432.
- **Local configuration permissions:** `.local` must be owned by you and mode `0700`; `.local/operator.env` must be owned by you and mode `0600`. A malformed or symlinked file is rejected.
- **Provisioning refused:** an existing operator was disabled or has a different subject. Review the operator row and the intended identity; startup will not overwrite it.
- **Migration/readiness failure:** inspect `docker compose -f infra/compose.yaml logs postgres api worker frontend` (or `docker-compose`). The launcher stops before app startup if migration or provisioning fails. PostgreSQL data is retained.
- **npm cache permission error during host `make setup`:** use `npm_config_cache="$(mktemp -d)" make setup`; do not use `sudo npm` or change ownership of unrelated data.
