#!/usr/bin/env python3
import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath


SENSITIVE_BASENAME_PATTERNS = (
    "*.key",
    "*.jks",
    "*.keystore",
    "*.p12",
    "*.pem",
    "*.pfx",
    "*.token",
    "*.tokens",
    "*.token.json",
    "*-token",
    "*-token.json",
    "*_token",
    "*_token.json",
    "*refresh-token*.json",
    "*refresh_token*.json",
    "client-secret*.json",
    "client_secret*.json",
    "client-secrets*.json",
    "client_secrets*.json",
    "credentials.json",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "oauth-client*.json",
    "oauth_client*.json",
    "service-account*.json",
    "service_account*.json",
    "token.json",
    "tokens.json",
)

MATERIAL_PATTERNS = (
    (
        "private key",
        re.compile(rb"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
    ),
    ("Google service account", re.compile(rb'"type"\s*:\s*"service_account"')),
    ("OAuth client secret", re.compile(rb'"client_secret"\s*:')),
    ("AWS access key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("GitHub token", re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}")),
    ("GitHub token", re.compile(rb"github_pat_[A-Za-z0-9_]{20,}")),
    ("Google API key", re.compile(rb"AIza[0-9A-Za-z_-]{20,}")),
    ("Slack token", re.compile(rb"xox[baprs]-[0-9A-Za-z-]{10,}")),
    ("Stripe live secret", re.compile(rb"sk_live_[0-9A-Za-z]{16,}")),
)


def tracked_files(root: Path) -> list[PurePosixPath]:
    completed = subprocess.run(
        ["git", "-C", root, "ls-files", "-z"],
        check=True,
        capture_output=True,
    )
    return [
        PurePosixPath(raw_path.decode("utf-8"))
        for raw_path in completed.stdout.split(b"\0")
        if raw_path
    ]


def filename_is_sensitive(path: PurePosixPath) -> bool:
    lowered_parts = tuple(part.lower() for part in path.parts)
    if ".vercel" in lowered_parts:
        return True
    lowered_name = path.name.lower()
    return any(
        fnmatch.fnmatchcase(lowered_name, pattern)
        for pattern in SENSITIVE_BASENAME_PATTERNS
    )


def find_violations(root: Path) -> tuple[list[tuple[str, str]], int]:
    paths = tracked_files(root)
    violations: set[tuple[str, str]] = set()

    for path in paths:
        display_path = path.as_posix()
        if filename_is_sensitive(path):
            violations.add((display_path, "sensitive filename"))

        content = (root / path).read_bytes()
        for label, pattern in MATERIAL_PATTERNS:
            if pattern.search(content):
                violations.add((display_path, label))

    return sorted(violations), len(paths)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check tracked files for high-signal credential material."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Git repository root (defaults to this script's repository).",
    )
    args = parser.parse_args()

    try:
        violations, file_count = find_violations(args.root.resolve())
    except (OSError, subprocess.CalledProcessError) as error:
        print(f"Secret scan could not inspect tracked files ({type(error).__name__}).", file=sys.stderr)
        return 2

    if violations:
        print("Secret scan failed: high-risk tracked material detected.", file=sys.stderr)
        for path, label in violations:
            print(f"- {path}: {label}", file=sys.stderr)
        return 1

    print(f"Secret scan passed: {file_count} tracked files checked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
