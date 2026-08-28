import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCANNER = REPOSITORY_ROOT / "scripts" / "check_secrets.py"


def initialize_repository(path: Path, files: dict[str, str]) -> None:
    subprocess.run(["git", "init", "--quiet", path], check=True)
    for relative_path, content in files.items():
        file_path = path / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
    subprocess.run(
        ["git", "-C", path, "add", "--force", "."],
        check=True,
        capture_output=True,
        text=True,
    )


def run_scan(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, SCANNER, "--root", path],
        capture_output=True,
        text=True,
        check=False,
    )


def test_secret_scan_accepts_safe_tracked_files(tmp_path: Path) -> None:
    initialize_repository(tmp_path, {"README.md": "safe public documentation\n"})

    completed = run_scan(tmp_path)

    assert completed.returncode == 0
    assert "Secret scan passed" in completed.stdout


def test_secret_scan_rejects_high_risk_tracked_filename_without_content(
    tmp_path: Path,
) -> None:
    secret_value = "do-not-print-this-client-secret"
    initialize_repository(
        tmp_path,
        {"config/client_secret_example.json": secret_value},
    )

    completed = run_scan(tmp_path)

    assert completed.returncode == 1
    assert "config/client_secret_example.json" in completed.stderr
    assert "sensitive filename" in completed.stderr
    assert secret_value not in completed.stderr


def test_secret_scan_rejects_high_signal_material_without_value(
    tmp_path: Path,
) -> None:
    secret_value = "ghp_" + "0123456789abcdefghijklmnopqrstuv"
    initialize_repository(tmp_path, {"notes.txt": secret_value})

    completed = run_scan(tmp_path)

    assert completed.returncode == 1
    assert "notes.txt" in completed.stderr
    assert "GitHub token" in completed.stderr
    assert secret_value not in completed.stderr
