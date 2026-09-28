# Local operator development

This is the private operator shell and L07 user-seeded experiment flow. Run from the repository root. The launcher reuses `infra/compose.yaml`, keeps all published ports on loopback, and leaves outreach disabled. Model calls are disabled by default.

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

## Manual R01A-UX experiment intake check

Provider execution stays disabled by default. For an isolated recorded run, use a separate Compose project and private auth file as described above. Set `ALON_AI_PROVIDER_MODE=fake` and an explicit positive `ALON_AI_IDEA_INTAKE_BUDGET_USD` in the terminal running `./scripts/local-dev.sh up`. The budget is trusted workspace policy for intake, not a form field or permission for a paid call. The API and worker use recorded synthetic responses through the governed Idea runtime and ledger; outreach remains disabled. Recorded advice is labeled in the browser and is not evidence of actual customer demand or a live OpenAI result.

The operator needs a previously saved, approved profile. A fresh operator without one receives `OPERATOR_PROFILE_REQUIRED`; the app does not invent capabilities, delivery limits, or commercial settings. Use the authenticated `POST /api/operator/idea-profile` setup command described below to save an explicitly approved profile before this check.

After signing in, open **New experiment**. Confirm the setup has one optional idea field. Enter a short idea and select **Start experiment**. The server saves the exact seed and starts one governed Idea refinement run. Refresh before accepting: the same run and advice should return, with no accepted idea yet. Use **Accept and save idea** only after reviewing the proposal, then refresh again to confirm the accepted version.

For the second path, open **New experiment** with an empty idea and select **Generate an idea**. Review the labeled proposals, edit one into a new immutable revision, regenerate from it, then choose a revision and select **Start experiment**. Refresh at each stage to confirm proposal lineage and the same run persist. A blocked or unavailable live provider must remain visibly blocked; it must not switch to recorded mode.

Unset `ALON_AI_PROVIDER_MODE` and `ALON_AI_IDEA_INTAKE_BUDGET_USD` before returning the stack to its default disabled configuration. Keep the same Compose project and port overrides for its lifecycle commands.

## R01A profile setup and saved run inspection

Set a positive `ALON_AI_IDEA_INTAKE_BUDGET_USD` for the API and worker before starting the local stack. This is a trusted admission limit, not a field in New experiment and not approval for a paid call. The worker must use the same provider mode and runtime configuration as the API. Recorded mode (`ALON_AI_PROVIDER_MODE=fake`) can be used for deterministic checks without a paid call.

After signing in, submit an approved operator profile once through the private browser proxy `POST /api/operator/idea-profile` (backend: `POST /operator/idea-profile`). Its JSON body is `{"profile":{"capabilities":[...],"constraints":[...],"delivery":{"max_project_hours":"...","hours_per_week":"...","concurrent_projects":1},"commercial":{"currency":"USD","hourly_cost":"...","minimum_project_price":"...","minimum_margin_rate":"...","maximum_discount_rate":"...","minimum_deposit_rate":"..."}}}`. Supply real reviewed values for the operator or explicitly labeled synthetic values in an isolated recorded test stack. The response gives `profile_id`, `profile_version`, and the configured `budget_usd`. Do not put credentials in this request.

Start an experiment from its multiline idea or generate, revise, and select a proposal. The service saves a run reference before returning. Open the experiment's saved URL and inspect the Agent run panel for the pinned inputs, retained output, status events, review state, receipt, and actual or pending cost. Refresh or reopen that URL to recover the same run. Rejecting the output and accepting its exact reviewed version are separate commands. A queued cancellation can be confirmed; a request made after dispatch may require reconciliation and cannot undo a provider effect. Do not retry an uncertain paid request with a new command key.

Live mode requires the separate reviewed model, rights, price, credential, and finite spend setup below, plus Alon's authorization for the actual paid call. A configured credential or a recorded run is not proof of live execution.

### Historical L07 OpenAI setup

The prior OpenAI-only L07 manifest and provisioner are retained for historical
replay. The local launcher now starts the R01A combined provider and does not
accept `ALON_AI_L07_LIVE_ACK` or `ALON_AI_L07_LIVE_MANIFEST` as live setup.
Follow the combined setup below for new local live runs.

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

## Reviewed R01A combined provider setup

Combined Idea execution requires OpenAI, Brave, and Firecrawl authority together.
Run the ordinary disabled stack once to create and identify the active local
operator. Then prepare the reviewed manifest and evidence. The live launcher
provisions the combined runtime under the API and worker UID in the same Compose
project. Provisioning makes no provider calls.

Prepare an owner-private directory (`0700`) containing a reviewed manifest and
its evidence documents, each regular file mode `0600`, with no symbolic or hard
links. The exact schema is `CombinedIdeaSetupManifest` in
`backend/src/alon_ai/services/combined_idea_provision.py`. Print its full JSON
schema without opening the database or prompting for keys:

```sh
cd backend
.venv/bin/python -m alon_ai.services.combined_idea_provision \
  --manifest /absolute/private/combined-manifest.json \
  --data-dir /absolute/private/provider-data --print-schema
```

The manifest contains `version: 1`, `config`, `authorities`, `proofs`,
`firecrawl_commercial_approvals`, and `research_model_use_approvals`. Supply the
actual reviewed values; there are no
production example grants, inferred rights, or default prices. `config` is the
exact `CombinedIdeaConfig`: model and per-call token caps, aggregate model request
and token limits, whole-run timeout, research policy, and capability bindings.
The research policy requires calls, pages, elapsed time, spend, results, PDF
bytes/pages/text, and parser CPU/memory/wall-time limits (`pdf_cpu_seconds`,
`pdf_memory_bytes`, `pdf_wall_seconds`). PDF capture requires Linux resource
limits and fails closed before spending a credit on unsupported hosts.
Research bindings are reviewed templates; the runtime derives immutable run
identities and budgets before execution. Their workflow/version UUIDs are not
permission to execute a different run.

Each authority supplies complete immutable `policy`, `grant`, `prices`, `fx`, and
`evidence` records matching the config, active operator, account, capability,
model, terms, scope, validity, and prices. Each evidence UUID must have exactly
one `proofs` entry containing a document filename next to the manifest and its
SHA-256 digest. Retain the reviewed documents for audit. The command checks their
bytes; the operator remains responsible for reviewing what they authorize.

Brave is limited to `OFFICIAL_SOURCE_IDENTIFICATION` with empty required and
stored fields and no retention policy. Search results and URLs remain ephemeral;
Brave search is not retained evidence. Every Firecrawl grant additionally needs
an approval tied to its grant evidence UUID, reviewed by the active operator,
with `express_commercial_use_authorized: true` and
`permitted_use: "R01A_COMMERCIAL_MARKET_RESEARCH"`. This attests that the retained
document expressly authorizes the intended commercial use. Possession of an API
key, a paid subscription, or a copy of public terms does not supply that approval.
Missing or mismatched commercial proof blocks setup.

Firecrawl `FIRECRAWL_PAGE_CAPTURE` bindings must explicitly request and be
licensed to retain both `URL` and `TEXT`: include both in
`config.intended_use.required_fields` and `grant.storage_fields`, with the
reviewed retention rule and positive retention duration. `TITLE` is optional.
These rights let the saved research case show the original source URL and its
permitted text while the grant and retention remain current. Missing source
fields block provisioning; the app never adds storage rights on the operator's
behalf. Brave remains ephemeral and gains no storage rights from this rule.

Both Brave and Firecrawl research grants must explicitly permit outbound use
(`outbound_use_permitted: true`) because their scoped tool results enter the
selected OpenAI model. For every research grant, `research_model_use_approvals`
must bind its grant evidence UUID to `outbound_to_openai_authorized: true`,
`permitted_use: "R01A_MODEL_CONSUMPTION"`, the exact approved OpenAI account handle
and model identifier, and the reviewing operator. The retained grant document
must support that permission: Firecrawl needs both commercial-use authorization
and authorization for the scoped data's disclosure to the selected LLM. Brave
outbound permission covers only ephemeral official-source URLs; it grants no
storage or retention rights. The OpenAI generation grant remains outbound-disabled.
Missing, different-destination, or unreviewed outbound rights block provisioning;
no permission is inferred from an API key or from enabling the combined runtime.

Research prices use USD per declared unit. Firecrawl Map is unavailable in the
R01A live demo: its API does not confirm billed credits, and unresolved accounting
prevents a combined run from completing. Both runtime configuration and reviewed
provisioning reject Map bindings until reconciliation support exists, including
included-credit plans. Use Brave plus Firecrawl page capture for the reviewed
demo. Supported research bounds are one request or captured page. PDF capture uses the approved raw PDF path with
server parsing disabled; local limits do not authorize additional remote parsing.
Model pricing uses the exact selected model and both input and output token
components. The model and research budgets and all controls remain enforced by
the existing governance ledger.

An included-credit research plan may use an actual marginal USD price of `0`.
Do not invent a positive allocation price and label it cash spend. Every such
provider/account requires an `included_research_credits` entry identifying the
exact zero-price IDs, their pricing evidence references, the control evidence
references, the reviewing operator, and a finite `included_credit_limit` with
`credit_unit: "PROVIDER_CREDIT"`. The reviewed evidence must confirm the remaining
included allowance and the account controls: `included_credits_confirmed: true`,
`pay_as_you_go_enabled: false`, and `automatic_topups_enabled: false`. Missing
proof or enabled paid overage blocks zero-price provisioning. This does not
authorize commercial use or disclosure to an LLM; those separate approvals above
remain required.

The sum of each covered capability's lifetime dispatch quota multiplied by its
maximum per-request credit quantity must fit the included allowance. Each quota
window, anchored at its policy effective time, must extend through the runtime's
expiry so it cannot replenish within the approval period. Keep the reviewed
validity short enough for those controls, and account for any use outside this
application when reviewing remaining credits. Per-run call/page/credit bounds
still apply. Receipts retain observed usage quantity with USD cost zero when
confirmed; unknown usage remains unresolved. These limits apply to included
credits; they do not turn OpenAI model pricing into a zero-price plan.

The launcher imports the reviewed manifest and only its referenced evidence
files from their owner-private host directory through a read-only mount. It
copies them temporarily into the private Compose volume under the app UID,
then removes those temporary copies after provisioning. The source directory
and files must be owned by the host operator and have modes `0700` and `0600`,
respectively. Run from a real terminal so all three API key prompts can suppress
echo. The finite budget and paid-call acknowledgment are required on every live
startup:

```sh
export ALON_AI_PROVIDER_MODE=live
export ALON_AI_IDEA_INTAKE_BUDGET_USD=<APPROVED_FINITE_USD_AMOUNT>
export ALON_AI_R01A_LIVE_ACK=I_ACCEPT_PAID_CALLS
export ALON_AI_R01A_LIVE_MANIFEST=/absolute/private/reviewed/combined-manifest.json
./scripts/local-dev.sh up
```

The launcher registers reviewed authority and prompts for each provider key on
first setup. It publishes the three encrypted, consumer-scoped stores and
`combined-live/combined-idea.json` in the Compose private volume. Later `up`
commands recheck the same reviewed manifest, evidence digests, active operator,
authority rows, and encrypted stores without asking for keys again. Changes
require a separately reviewed rotation; provisioning will not overwrite an
existing configuration. An interrupted process can leave an unpublished
`.combined-stage-*` directory, which needs deliberate operator cleanup. The
launcher also removes its temporary `.combined-review-input` copy on ordinary
failure or interruption; a forced container or host shutdown can leave this
copy in the private volume until the next live startup, which replaces it.

Both API and worker receive the same `ALON_AI_PROVIDER_MODE=live`,
`ALON_AI_R01A_LIVE_CONFIG_PATH=/app/.local/combined-live/combined-idea.json`,
and finite `ALON_AI_IDEA_INTAKE_BUDGET_USD`; they mount the same private volume
read-only. Provider execution still requires reviewed authority at dispatch and
a separate browser cost acknowledgment. Do not use a synthetic test manifest
as production authority. No live paid call is part of automated verification.
