# Local operator development

This is the private operator shell and L07 user-seeded experiment flow. Run from the repository root. The launcher reuses `infra/compose.yaml`, keeps all published ports on loopback, and leaves outreach disabled. Model calls are disabled by default.

## Prerequisites

- A running Docker engine and either the `docker compose` plugin or standalone `docker-compose` CLI.
- Python 3 with `hashlib.scrypt` and `curl` on the host. The application itself runs in containers; host `uv` and Node are needed only for host development and tests.
- Free loopback ports 3000, 8000, and 5432, or set `ALON_AI_FRONTEND_PORT`, `ALON_AI_API_PORT`, and `ALON_AI_POSTGRES_PORT` to three distinct free ports before starting a mode.

On macOS, Docker Desktop or Colima can provide the engine. With Colima and the Homebrew standalone Compose CLI:

```sh
colima start
export COMPOSE=docker-compose
```

Keep these variables in the same terminal for all launcher commands. If using Docker Desktop with its Compose plugin, no override is needed.

## Start a mode

```sh
make local-disabled
make local-fake
make local-live
make local-status
make local-down
```

Choose exactly one start command for the provider mode you want. `local-disabled` is the safe default, `local-fake` uses synthetic recorded results, and `local-live` uses the real OpenAI, Brave, and Firecrawl integrations with the approved `$0.25` application budget. The mode commands set their own configuration; you do not need to export provider-mode, budget, or paid-call acknowledgment variables.

The local live key file is `.local/live-keys.env`. Create it with private permissions inside the ignored `.local` directory. Put the three keys on these lines, without quotes:

```dotenv
OPENAI_API_KEY=your-openai-key
BRAVE_API_KEY=your-brave-key
FIRECRAWL_API_KEY=your-firecrawl-key
```

The file must remain mode `0600` inside the owner-only `.local` directory (`0700`). The live launcher reads it without executing it as shell code. Only the one-time provisioner receives it; the API and worker get separate encrypted, provider-scoped credentials. Do not put these keys in `.env`, `.env.example`, `.local/operator.env`, source code, or chat.

`make local-live` also requires the reviewed provider authority bundle at `.local/live-authority.json`, with its reviewed evidence documents alongside it. This bundle records the provider/account rights and the approved quotas; the key file cannot establish those facts. This run records an operator-attested personal, noncommercial purpose, limited to Firecrawl page capture. Commercial Firecrawl use still requires express provider authorization. Credit balances and account controls are reviewed separately from either use classification. If the bundle is missing or incomplete, live startup stops before any provider request.

On first use, any mode checks Docker and local ports, then prompts for a local sign-in password twice without echoing it. Choose a unique password of 12 to 1024 characters. The launcher stores only its scrypt verifier and a random session signing key in `.local/operator.env`; it reuses this file later. If the Compose project's PostgreSQL volume exists but this verifier file is missing, startup refuses to create replacement credentials.

The launcher starts PostgreSQL, applies Alembic migrations, provisions the local operator, applies the DBOS schema, then starts the API, worker, and frontend. It waits for container health and checks the API and frontend over loopback. Open the printed sign-in URL (default <http://localhost:3000/login>) and use the local password. The local subject is `local-operator@alon.ai`, and the provisioner displays the operator as `Alon`. Exported operator verifier or signing-key variables are ignored; the validated private file supplies them to Compose.

The provisioner refuses a disabled operator or an already active operator with a different subject. It does not replace that row. Resolve that state deliberately; do not delete the PostgreSQL volume to bypass it. If the local verifier file is lost while the database remains, `up` refuses to generate a replacement. Restore it from a secure backup or use an explicit, separately reviewed credential rotation procedure.

`make local-down` stops containers and retains the PostgreSQL volume and local configuration. It does not use `--volumes`. The mode commands are also available directly as `./scripts/local-dev.sh disabled|fake|live`; lifecycle commands are `down`, `status`, and `help`. By default, the launcher derives a stable Compose project name from this checkout's physical path, so another checkout uses different containers and a different PostgreSQL volume. Set `COMPOSE_PROJECT_NAME` explicitly to select a project; use the same value for every lifecycle command.

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
5. Log out. Browser back/refresh and the API's private endpoints should no longer expose prior operator data. Sign in again, then `make local-down`, `make local-disabled`, and confirm the original password still works.
6. For a failure drill, stop PostgreSQL via Compose and refresh status. The UI should show an unavailable state rather than retaining a healthy claim; restore with `make local-disabled`.

Do not paste login cookies, verifier, signing key, or passwords into bug reports or logs. This local stack uses example database credentials and HTTP on loopback. It is not a public deployment.

## Manual R01A-UX experiment intake check

Provider execution stays disabled in `make local-disabled`. For an isolated recorded run, use a separate Compose project and private auth file as described above, then run `make local-fake`. The launcher applies the fixed recorded-mode budget automatically. The API and worker use synthetic responses through the governed Idea runtime and ledger; outreach remains disabled. Recorded advice is labeled in the browser and is not evidence of customer demand or a live OpenAI result.

The operator needs a previously saved, approved profile. A fresh operator without one receives `OPERATOR_PROFILE_REQUIRED`; the app does not invent capabilities, delivery limits, or commercial settings. Use the authenticated `POST /api/operator/idea-profile` setup command described below to save an explicitly approved profile before this check.

After signing in, open **New experiment**. Confirm the setup has one optional idea field. Enter a short idea and select **Start experiment**. The server saves the exact seed and starts one governed Idea refinement run. Refresh before accepting: the same run and advice should return, with no accepted idea yet. Use **Accept and save idea** only after reviewing the proposal, then refresh again to confirm the accepted version.

For the second path, open **New experiment** with an empty idea and select **Generate an idea**. Review the labeled proposals, edit one into a new immutable revision, regenerate from it, then choose a revision and select **Start experiment**. Refresh at each stage to confirm proposal lineage and the same run persist. A blocked or unavailable live provider must remain visibly blocked; it must not switch to recorded mode.

Run `make local-disabled` when you want to switch the same stack back to disabled mode. The launcher clears mode-specific values while preserving the selected Compose project and port overrides.

## R01A profile setup and saved run inspection

The mode commands give the API and worker the same provider mode and fixed admission limit. The recorded mode (`make local-fake`) supports deterministic checks without paid calls.

After signing in, submit an approved operator profile once through the private browser proxy `POST /api/operator/idea-profile` (backend: `POST /operator/idea-profile`). Its JSON body is `{"profile":{"capabilities":[...],"constraints":[...],"delivery":{"max_project_hours":"...","hours_per_week":"...","concurrent_projects":1},"commercial":{"currency":"USD","hourly_cost":"...","minimum_project_price":"...","minimum_margin_rate":"...","maximum_discount_rate":"...","minimum_deposit_rate":"..."}}}`. Supply real reviewed values for the operator or explicitly labeled synthetic values in an isolated recorded test stack. The response gives `profile_id`, `profile_version`, and the configured `budget_usd`. Do not put credentials in this request.

Start an experiment from its multiline idea or generate, revise, and select a proposal. The service saves a run reference before returning. Open the experiment's saved URL and inspect the Agent run panel for the pinned inputs, retained output, status events, review state, receipt, and actual or pending cost. Refresh or reopen that URL to recover the same run. Rejecting the output and accepting its exact reviewed version are separate commands. A queued cancellation can be confirmed; a request made after dispatch may require reconciliation and cannot undo a provider effect. Do not retry an uncertain paid request with a new command key.

Live mode requires the separate reviewed model, rights, price, credential, and finite spend setup below, plus Alon's authorization for the actual paid call. A configured credential or a recorded run is not proof of live execution.

### Historical L07 OpenAI setup

The prior OpenAI-only L07 manifest and provisioner are retained for historical
replay. The local launcher now starts the R01A combined provider and does not
accept `ALON_AI_L07_LIVE_ACK` or `ALON_AI_L07_LIVE_MANIFEST` as live setup.
Follow the combined setup below for new local live runs.

## Development and verification

The repository's existing `make setup`, `make generate`, `make lint`, `make typecheck`, `make test`, `make build`, and `make test-integration` targets remain available. `make dev` is the earlier general Compose path; use `make local-disabled`, `make local-fake`, or `make local-live` for the provisioned local operator stack. Direct host API/worker development needs `ALON_AI_DATABASE_URL`, `ALON_AI_DBOS_SYSTEM_DATABASE_URL`, `ALON_AI_OPERATOR_AUTH_SUBJECT`, `ALON_AI_OPERATOR_PASSWORD_HASH`, and `ALON_AI_SESSION_SIGNING_KEY` set privately, plus the configured host port. Do not source `.local/operator.env` into a shared shell or print it while debugging.

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

## Reviewed R01A combined provider setup
## Live provider approval and execution

`make local-live` chooses live mode, applies the approved `$0.25` application
budget, reads `.local/live-keys.env`, and loads the reviewed authority bundle
from `.local/live-authority.json`. You do not export provider-mode, budget,
manifest-path, or paid-call acknowledgment settings. On first live setup, the
three key values are imported into separate encrypted provider stores. Starting
or provisioning the project itself makes no provider request; paid requests
start only when you trigger a run in the signed-in UI and acknowledge its cost.

The authority bundle is a separate reviewed record; credentials cannot stand in
for provider permissions. It must document `gpt-6-luna` with maximum reasoning,
no more than 12 OpenAI requests / 250,000 input tokens / 24,000 output tokens
and `$0.20`; no more than six Brave searches and `$0.05`, with Brave results
kept ephemeral; and no more than eight Firecrawl captures from confirmed
included credits, with paid overage and automatic top-ups disabled. The total
application budget is `$0.25`.

The reviewed bundle records this run as your personal, noncommercial test. Its
Firecrawl scope is limited to capturing page URLs and text and disclosing that
research to the selected OpenAI account/model. Commercial Firecrawl use still
requires express provider authorization. The account evidence must support the
actual prices and included-credit balance. These checks remain mandatory and
fail closed. A missing or unsupported permission stops live startup before any
provider call. Do not replace real evidence with a synthetic manifest or a
self-generated claim of provider authorization.

The live key file is parsed as data, never sourced by a shell, and is mounted
only for the one-time provisioner. The reviewed manifest and evidence are
copied temporarily into the private Docker volume and removed after
provisioning. The running API and worker receive encrypted consumer-scoped
stores read-only. A changed key or authority requires a separately reviewed
rotation.

The authoritative schema is `CombinedIdeaSetupManifest` in
`backend/src/alon_ai/services/combined_idea_provision.py`. Provider execution
also rechecks the reviewed permissions, quotas, current authority, and source
rights at dispatch. Automated verification never calls paid providers.
