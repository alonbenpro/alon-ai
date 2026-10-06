"""Behavioral checks for the local operator launcher without touching Docker."""

import os
import pty
import select
import socket
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/local-dev.sh"


class LocalDevTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "infra").mkdir()
        (self.root / "infra/compose.yaml").write_text("services: {}\n")
        (self.root / ".env.example").write_text("ALON_AI_ENVIRONMENT=development\n")
        if SCRIPT.exists():
            (self.root / "scripts/local-dev.sh").write_bytes(SCRIPT.read_bytes())
        self.bin = self.root / "bin"
        self.bin.mkdir()
        docker = self.bin / "docker"
        docker.write_text(
            "#!/bin/sh\n"
            "printf 'project=%s mode=%s budget=%s auth_env=%s/%s %s\\n' \"${COMPOSE_PROJECT_NAME:-default}\" \"${ALON_AI_PROVIDER_MODE:-unset}\" \"${ALON_AI_IDEA_INTAKE_BUDGET_USD:-unset}\" \"${ALON_AI_OPERATOR_PASSWORD_HASH+set}\" \"${ALON_AI_SESSION_SIGNING_KEY+set}\" \"$*\" >> \"$FAKE_DOCKER_LOG\"\n"
            "if [ \"${FAKE_REQUIRE_DOCKER_CREDENTIAL_HELPER:-0}\" = 1 ]; then command -v docker-credential-desktop >/dev/null 2>&1 || exit 88; fi\n"
            "if [ \"$1\" = info ] && [ \"${FAKE_DOCKER_DOWN:-0}\" = 1 ]; then exit 1; fi\n"
            "case \"$*\" in\n"
            "  *'config --format json'*) printf 'volume=%s_postgres_data\\n' \"${COMPOSE_PROJECT_NAME:-default}\" >> \"$FAKE_DOCKER_LOG\"; printf '{\"volumes\":{\"postgres_data\":{\"name\":\"%s_postgres_data\"}}}\\n' \"${COMPOSE_PROJECT_NAME:-default}\"; exit 0;;\n"
            "  *'up -d --wait postgres'*) printf 'volume=%s_postgres_data\\n' \"${COMPOSE_PROJECT_NAME:-default}\" >> \"$FAKE_DOCKER_LOG\";;\n"
            "esac\n"
            "if [ \"$1 $2\" = 'volume ls' ] && [ \"${FAKE_VOLUME_PRESENT:-0}\" = 1 ]; then printf '%s_postgres_data\\n' \"${COMPOSE_PROJECT_NAME:-default}\"; exit 0; fi\n"
            "if [ -n \"${FAKE_FAIL_CONTAINS:-}\" ]; then case \"$*\" in *\"$FAKE_FAIL_CONTAINS\"*) exit 1;; esac; fi\n"
            "case \"$*\" in *'live-provision python - live-authority.json'*) [ \"${FAKE_BAD_LIVE_MOUNT:-0}\" != 1 ]; exit $?;; esac\n"
            "case \"$*\" in *'ps --status running --services worker'*) [ \"${FAKE_WORKER_DOWN:-0}\" = 1 ] || printf '%s\\n' worker; exit 0;; esac\n"
            "if [ \"$1\" = compose ] && [ \"$2\" = version ]; then [ \"${FAKE_COMPOSE_PLUGIN_DOWN:-0}\" != 1 ]; exit $?; fi\n"
            "if [ \"$1\" = compose ] && [ \"$2\" = ps ]; then exit 0; fi\n"
            "exit 0\n"
        )
        docker.chmod(0o755)
        standalone = self.bin / "docker-compose"
        standalone.write_bytes(docker.read_bytes())
        standalone.chmod(0o755)
        curl = self.bin / "curl"
        curl.write_text("#!/bin/sh\nexit 0\n")
        curl.chmod(0o755)
        python = self.bin / "python3"
        python.write_text(
            "#!/bin/sh\n"
            "case \"$2\" in\n"
            "  5432|55432) if [ \"${FAKE_REAL_PORT_CHECK:-0}\" != 1 ]; then cat >/dev/null; exit 0; fi ;;\n"
            "esac\n"
            f"exec '{os.path.realpath(os.sys.executable)}' \"$@\"\n"
        )
        python.chmod(0o755)
        self.log = self.root / "docker.log"

    def run_script(self, *args, extra_env=None, checkout=None):
        env = dict(os.environ)
        for name in ("COMPOSE_PROJECT_NAME", "ALON_AI_OPERATOR_PASSWORD_HASH", "ALON_AI_SESSION_SIGNING_KEY"):
            env.pop(name, None)
        env.update(
            PATH=f"{self.bin}:{env.get('PATH', '')}",
            FAKE_DOCKER_LOG=str(self.log),
        )
        env.update(extra_env or {})
        return subprocess.run(
            ["sh", str((checkout or self.root) / "scripts/local-dev.sh"), *args],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def write_auth(self):
        local = self.root / ".local"
        local.mkdir(mode=0o700)
        secret = local / "operator.env"
        secret.write_text(
            "ALON_AI_OPERATOR_PASSWORD_HASH='scrypt$16384$8$1$"
            + "a" * 32
            + "$"
            + "b" * 64
            + "'\nALON_AI_SESSION_SIGNING_KEY='"
            + "c" * 64
            + "'\n"
        )
        secret.chmod(0o600)
        return secret

    def write_review_manifest(self):
        manifest = self.root / ".local/live-authority.json"
        manifest.write_text('{"proofs":[{"document":"proof.txt"}]}\n')
        manifest.chmod(0o600)
        proof = manifest.parent / "proof.txt"
        proof.write_text("reviewed evidence\n")
        proof.chmod(0o600)
        return manifest

    def write_live_keys(self):
        local = self.root / ".local"
        local.mkdir(mode=0o700, exist_ok=True)
        keys = local / "live-keys.env"
        keys.write_text(
            "OPENAI_API_KEY=synthetic-openai\n"
            "BRAVE_API_KEY=synthetic-brave\n"
            "FIRECRAWL_API_KEY=synthetic-firecrawl\n"
        )
        keys.chmod(0o600)
        return keys

    def test_help_lists_lifecycle_commands(self):
        result = self.run_script("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("disabled", result.stdout)
        self.assertIn("fake", result.stdout)
        self.assertIn("live", result.stdout)
        self.assertIn("down", result.stdout)
        self.assertIn("status", result.stdout)

    def test_docker_desktop_helper_is_found_in_user_docker_bin(self):
        home = self.root / "home"
        helper_dir = home / ".docker/bin"
        helper_dir.mkdir(parents=True)
        helper = helper_dir / "docker-credential-desktop"
        helper.write_text("#!/bin/sh\nexit 0\n")
        helper.chmod(0o755)

        result = self.run_script(
            "status",
            extra_env={
                "HOME": str(home),
                "FAKE_REQUIRE_DOCKER_CREDENTIAL_HELPER": "1",
            },
        )

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_disabled_command_forces_provider_mode_off(self):
        self.write_auth()
        result = self.run_script(
            "disabled",
            extra_env={
                "ALON_AI_PROVIDER_MODE": "live",
                "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text()
        self.assertIn("mode=disabled budget=unset", commands)
        self.assertNotIn("combined_idea_provision", commands)

    def test_fake_command_uses_recorded_mode_and_fixed_test_budget(self):
        self.write_auth()
        result = self.run_script(
            "fake", extra_env={"ALON_AI_PROVIDER_MODE": "live"}
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mode=fake budget=0.25", self.log.read_text())

    def test_live_command_reads_local_keys_without_exported_setup_values(self):
        self.write_auth()
        manifest = self.write_review_manifest()
        self.write_live_keys()
        result = self.run_script("live")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text()
        self.assertIn("mode=live budget=0.20", commands)
        self.assertIn("--keys-file /app/.local/.combined-review-input/live-keys.env", commands)
        self.assertIn(":/app/reviewed-input:ro", commands)
        self.assertIn("python - live-authority.json", commands)
        self.assertNotIn("synthetic-openai", commands)
        self.assertNotIn("synthetic-brave", commands)
        self.assertNotIn("synthetic-firecrawl", commands)

    def test_live_command_requires_private_key_file_before_docker(self):
        self.write_auth()
        self.write_review_manifest()
        result = self.run_script("live")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(".local/live-keys.env", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_command_rejects_public_key_file_before_docker(self):
        self.write_auth()
        self.write_review_manifest()
        keys_file = self.write_live_keys()
        keys_file.chmod(0o644)
        result = self.run_script("live")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mode 0600", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_command_rejects_unfilled_key_template_before_docker(self):
        self.write_auth()
        self.write_review_manifest()
        keys_file = self.write_live_keys()
        keys_file.write_text(
            "OPENAI_API_KEY=\nBRAVE_API_KEY=\nFIRECRAWL_API_KEY=\n"
        )
        keys_file.chmod(0o600)
        result = self.run_script("live")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("all three provider keys", result.stderr)
        self.assertFalse(self.log.exists())

    def test_help_does_not_need_python_or_docker(self):
        (self.bin / "python3").write_text("#!/bin/sh\nexit 86\n")
        result = self.run_script("help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Usage:", result.stdout)

    def test_live_provider_requires_explicit_paid_call_acknowledgment(self):
        result = self.run_script(
            "up", extra_env={"ALON_AI_PROVIDER_MODE": "live"}
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit local-live command", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_provider_requires_manifest_before_first_provisioning(self):
        self.write_auth()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_PROVIDER_MODE": "live",
                "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
                "ALON_AI_POSTGRES_PORT": "55432",
                "ALON_AI_API_PORT": "18000",
                "ALON_AI_FRONTEND_PORT": "13000",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authority bundle is missing", result.stderr)

    def test_legacy_openai_setup_does_not_enable_combined_live_mode(self):
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_PROVIDER_MODE": "live",
                "ALON_AI_L07_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
                "ALON_AI_L07_LIVE_MANIFEST": "/tmp/old-live-authority.json",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("explicit local-live command", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_provider_requires_finite_budget(self):
        self.write_auth()
        manifest = self.write_review_manifest()
        keys_file = self.write_live_keys()
        for value in ("", "NaN", "Infinity", "0", "1.001"):
            with self.subTest(value=value):
                result = self.run_script(
                    "up",
                    extra_env={
                        "ALON_AI_PROVIDER_MODE": "live",
                        "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
                        "ALON_AI_R01A_LIVE_MANIFEST": str(manifest),
                        "ALON_AI_R01A_LIVE_KEYS_FILE": str(keys_file),
                        "ALON_AI_IDEA_INTAKE_BUDGET_USD": value,
                    },
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Live budget" if not value else "budget", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_provider_rejects_nonprivate_evidence_before_docker(self):
        self.write_auth()
        manifest = self.write_review_manifest()
        keys_file = self.write_live_keys()
        (manifest.parent / "proof.txt").chmod(0o644)
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_PROVIDER_MODE": "live",
                "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
                "ALON_AI_R01A_LIVE_MANIFEST": str(manifest),
                "ALON_AI_R01A_LIVE_KEYS_FILE": str(keys_file),
                "ALON_AI_IDEA_INTAKE_BUDGET_USD": "1.00",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("reviewed evidence", result.stderr)
        self.assertFalse(self.log.exists())

    def test_live_provider_replays_combined_provisioning_after_explicit_ack(self):
        self.write_auth()
        manifest = self.write_review_manifest()
        keys_file = self.write_live_keys()
        common = {
            "ALON_AI_PROVIDER_MODE": "live",
            "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
            "ALON_AI_R01A_LIVE_MANIFEST": str(manifest),
            "ALON_AI_R01A_LIVE_KEYS_FILE": str(keys_file),
            "ALON_AI_IDEA_INTAKE_BUDGET_USD": "1.00",
            "ALON_AI_POSTGRES_PORT": "55432",
            "ALON_AI_API_PORT": "18000",
            "ALON_AI_FRONTEND_PORT": "13000",
        }
        result = self.run_script("up", extra_env=common)
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text()
        self.assertIn("live-provision sh -c chown 10001:10001", commands)
        self.assertIn("python -m alon_ai.services.combined_idea_provision", commands)
        self.assertNotIn("python -m alon_ai.services.live_idea_provision", commands)
        self.assertIn("/app/.local/.combined-review-input/live-authority.json", commands)
        self.assertIn("--keys-file /app/.local/.combined-review-input/live-keys.env", commands)
        self.assertIn(":/app/reviewed-input:ro", commands)
        self.assertNotIn("OPENAI_API_KEY", commands)
        self.log.unlink()
        result = self.run_script("up", extra_env=common)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "python -m alon_ai.services.combined_idea_provision", self.log.read_text()
        )

    def test_live_manifest_import_must_succeed_before_provisioning(self):
        self.write_auth()
        manifest = self.write_review_manifest()
        keys_file = self.write_live_keys()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_PROVIDER_MODE": "live",
                "ALON_AI_R01A_LIVE_ACK": "I_ACCEPT_PAID_CALLS",
                "ALON_AI_R01A_LIVE_MANIFEST": str(manifest),
                "ALON_AI_R01A_LIVE_KEYS_FILE": str(keys_file),
                "ALON_AI_IDEA_INTAKE_BUDGET_USD": "1.00",
                "ALON_AI_POSTGRES_PORT": "55432",
                "ALON_AI_API_PORT": "18000",
                "ALON_AI_FRONTEND_PORT": "13000",
                "FAKE_BAD_LIVE_MOUNT": "1",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("authority/evidence import failed", result.stderr)
        self.assertNotIn(
            "python -m alon_ai.services.combined_idea_provision", self.log.read_text()
        )

    def test_down_preserves_database_volume(self):
        result = self.run_script("down")
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = self.log.read_text()
        self.assertIn("down", commands)
        self.assertNotIn("--volumes", commands)
        self.assertNotIn("-v", commands)

    def test_up_reuses_verifier_and_runs_provisioning_before_services(self):
        auth = self.write_auth()
        before = auth.read_bytes()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_POSTGRES_PORT": "55432",
                "ALON_AI_API_PORT": "18000",
                "ALON_AI_FRONTEND_PORT": "13000",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(auth.read_bytes(), before)
        commands = self.log.read_text()
        self.assertIn("up -d --wait postgres", commands)
        self.assertIn("alembic upgrade head", commands)
        self.assertIn("provision_operator.py", commands)
        self.assertIn("dbos migrate", commands)
        self.assertIn("up -d --wait api worker frontend", commands)
        self.assertLess(commands.index("alembic upgrade head"), commands.index("provision_operator.py"))
        self.assertLess(commands.index("provision_operator.py"), commands.index("up -d --wait api worker frontend"))
        self.assertIn("http://localhost:13000/login", result.stdout)
        self.assertNotIn("scrypt$", result.stdout + result.stderr + commands)

    def test_exported_auth_cannot_override_validated_private_file(self):
        self.write_auth()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_POSTGRES_PORT": "55432",
                "ALON_AI_OPERATOR_PASSWORD_HASH": "injected-verifier",
                "ALON_AI_SESSION_SIGNING_KEY": "injected-key",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("auth_env=set", self.log.read_text())
        self.assertIn("--env-file", self.log.read_text())
        self.assertNotIn("injected-", result.stdout + result.stderr + self.log.read_text())

    def test_default_projects_and_volumes_are_isolated_by_checkout(self):
        self.write_auth()
        other = self.root / "another-checkout"
        (other / "scripts").mkdir(parents=True)
        (other / "infra").mkdir()
        (other / "scripts/local-dev.sh").write_bytes(SCRIPT.read_bytes())
        (other / "infra/compose.yaml").write_text("services: {}\n")
        (other / ".env.example").write_text("ALON_AI_ENVIRONMENT=development\n")
        other_local = other / ".local"
        other_local.mkdir(mode=0o700)
        other_secret = other_local / "operator.env"
        other_secret.write_bytes((self.root / ".local/operator.env").read_bytes())
        other_secret.chmod(0o600)
        env = {"ALON_AI_POSTGRES_PORT": "55432"}

        first = self.run_script("up", extra_env=env)
        self.assertEqual(first.returncode, 0, first.stderr)
        first_log = self.log.read_text()
        first_project = first_log.split("project=", 1)[1].split()[0]
        self.assertNotEqual(first_project, "default")
        self.assertIn(f"volume={first_project}_postgres_data", first_log)

        self.log.write_text("")
        second = self.run_script("up", extra_env=env, checkout=other)
        self.assertEqual(second.returncode, 0, second.stderr)
        second_log = self.log.read_text()
        second_project = second_log.split("project=", 1)[1].split()[0]
        self.assertNotEqual(second_project, first_project)
        self.assertIn(f"volume={second_project}_postgres_data", second_log)

        self.log.write_text("")
        stopped = self.run_script("down")
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn(f"project={first_project}", self.log.read_text())
        self.assertNotIn(f"project={second_project}", self.log.read_text())
        self.assertNotIn("--volumes", self.log.read_text())

    def test_docker_failure_does_not_create_secrets(self):
        result = self.run_script("up", extra_env={"FAKE_DOCKER_DOWN": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Docker", result.stderr)
        self.assertFalse((self.root / ".local/operator.env").exists())

    def test_first_run_requires_terminal_for_password(self):
        result = self.run_script("up")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("terminal", result.stderr)
        self.assertFalse((self.root / ".local/operator.env").exists())

    def test_first_run_refuses_existing_database_volume(self):
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_POSTGRES_PORT": "55432",
                "FAKE_VOLUME_PRESENT": "1",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PostgreSQL data already exists", result.stderr)
        self.assertFalse((self.root / ".local/operator.env").exists())

    def test_rejects_conflicting_host_ports_before_startup(self):
        self.write_auth()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_POSTGRES_PORT": "55432",
                "ALON_AI_API_PORT": "18000",
                "ALON_AI_FRONTEND_PORT": "18000",
                "FAKE_REAL_PORT_CHECK": "1",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must be distinct", result.stderr)
        self.assertNotIn("up -d", self.log.read_text())

    def test_rejects_occupied_host_port_before_startup(self):
        self.write_auth()
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            occupied = str(listener.getsockname()[1])
            result = self.run_script(
                "up",
                extra_env={
                    "ALON_AI_POSTGRES_PORT": occupied,
                    "ALON_AI_API_PORT": "18000",
                    "ALON_AI_FRONTEND_PORT": "13000",
                    "FAKE_REAL_PORT_CHECK": "1",
                },
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"port {occupied} is occupied", result.stderr)
        self.assertNotIn("up -d", self.log.read_text())

    def test_rejects_insecure_existing_secret_file(self):
        auth = self.write_auth()
        auth.chmod(0o644)
        result = self.run_script("up")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("permissions", result.stderr)
        self.assertNotIn("up -d", self.log.read_text())

    def test_standalone_compose_override(self):
        result = self.run_script("down", extra_env={"COMPOSE": "docker-compose"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("down", self.log.read_text())

    def test_standalone_compose_is_detected_without_override(self):
        result = self.run_script("down", extra_env={"FAKE_COMPOSE_PLUGIN_DOWN": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("compose version", self.log.read_text())
        self.assertIn("down", self.log.read_text())

    def test_live_provisioner_uses_configured_local_operator_subject(self):
        compose = (ROOT / "infra/compose.yaml").read_text()
        provisioner = compose.split("  live-provision:\n", 1)[1].split(
            "\n  frontend:", 1
        )[0]

        self.assertIn(
            "ALON_AI_OPERATOR_AUTH_SUBJECT: local-operator@alon.ai", provisioner
        )

    def test_isolated_project_and_secret_path(self):
        private = self.root / "private"
        private.mkdir(mode=0o700)
        auth = self.write_auth()
        custom = private / "operator.env"
        custom.write_bytes(auth.read_bytes())
        custom.chmod(0o600)
        auth.unlink()
        result = self.run_script(
            "up",
            extra_env={
                "COMPOSE_PROJECT_NAME": "l05_disposable",
                "ALON_AI_LOCAL_AUTH_FILE": str(custom),
                "ALON_AI_POSTGRES_PORT": "55432",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(auth.exists())
        self.assertIn("project=l05_disposable", self.log.read_text())

    def test_provisioning_failure_does_not_start_app(self):
        self.write_auth()
        result = self.run_script(
            "up",
            extra_env={
                "ALON_AI_POSTGRES_PORT": "55432",
                "FAKE_FAIL_CONTAINS": "provision_operator.py",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Operator provisioning failed", result.stderr)
        self.assertNotIn("up -d --wait api worker frontend", self.log.read_text())

    def test_up_reports_worker_that_exits_after_startup(self):
        self.write_auth()
        result = self.run_script(
            "up",
            extra_env={"ALON_AI_POSTGRES_PORT": "55432", "FAKE_WORKER_DOWN": "1"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Worker exited", result.stderr)

    def test_first_run_never_echoes_password_when_terminal_is_restricted(self):
        env = dict(os.environ)
        env.update(
            PATH=f"{self.bin}:{env.get('PATH', '')}",
            FAKE_DOCKER_LOG=str(self.log),
            ALON_AI_POSTGRES_PORT="55432",
        )
        pid, master = pty.fork()
        if pid == 0:
            os.execve("/bin/sh", ["sh", str(self.root / "scripts/local-dev.sh"), "up"], env)
        transcript = bytearray()
        sent_first = sent_second = False
        while True:
            readable, _, _ = select.select([master], [], [], 5)
            self.assertTrue(readable, "first-run prompt did not progress")
            try:
                chunk = os.read(master, 4096)
            except OSError:
                break
            if not chunk:
                break
            transcript.extend(chunk)
            if b"Create local operator password:" in transcript and not sent_first:
                os.write(master, b"a-private-password-123\n")
                sent_first = True
            if b"Confirm local operator password:" in transcript and not sent_second:
                os.write(master, b"a-private-password-123\n")
                sent_second = True
        _, status = os.waitpid(pid, 0)
        os.close(master)
        exit_code = os.waitstatus_to_exitcode(status)
        self.assertNotIn(b"a-private-password-123", transcript)
        auth = self.root / ".local/operator.env"
        if exit_code:
            self.assertIn(b"terminal cannot suppress password echo", transcript)
            self.assertFalse(auth.exists())
            return
        self.assertEqual(stat.S_IMODE(auth.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(auth.parent.stat().st_mode), 0o700)
        self.assertNotIn("a-private-password-123", auth.read_text())


if __name__ == "__main__":
    unittest.main()
