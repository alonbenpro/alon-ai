import json
import os
import stat
from pathlib import Path

import pytest
from pydantic import SecretStr


def store(root: Path, **overrides):
    from alon_ai.security.secrets import EncryptedFileSecretStore

    return EncryptedFileSecretStore(
        root,
        **{
            "consumer": "openai-adapter",
            "allowed_handles": {"api-main", "api-other"},
            "keys": {"v1": b"a" * 32},
            "active_key_version": "v1",
            **overrides,
        },
    )


def test_roundtrip_uses_ciphertext_and_owner_only_permissions(tmp_path) -> None:
    root = tmp_path / "secrets"
    reader = store(root)
    reader.put("api-main", SecretStr("synthetic-private-value"))
    result = reader.get("api-main")
    assert isinstance(result, SecretStr)
    assert result.get_secret_value() == "synthetic-private-value"
    assert "synthetic-private-value" not in repr(reader)
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    files = list(root.iterdir())
    assert len(files) == 1
    assert b"synthetic-private-value" not in files[0].read_bytes()
    assert b"a" * 32 not in files[0].read_bytes()
    assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
    first = files[0].read_bytes()
    reader.put("api-main", SecretStr("synthetic-private-value"))
    assert files[0].read_bytes() != first
    assert len(list(root.iterdir())) == 1


def test_unauthorized_consumer_and_handle_are_denied(tmp_path) -> None:
    from alon_ai.security.secrets import SecretStoreError

    reader = store(tmp_path / "secrets")
    reader.put("api-main", SecretStr("private-value"))
    for other in (
        store(reader.root, consumer="other-adapter"),
        store(reader.root, allowed_handles=set()),
    ):
        with pytest.raises(SecretStoreError):
            other.get("api-main")
    with pytest.raises(SecretStoreError):
        reader.put("not-allowed", SecretStr("private-value"))


@pytest.mark.parametrize(
    "handle", ["../escape", "/absolute", "bad/name", "", "a" * 65, "a\x00b"]
)
def test_unsafe_handles_are_rejected(tmp_path, handle) -> None:
    from alon_ai.security.secrets import SecretStoreError

    with pytest.raises(SecretStoreError):
        store(tmp_path / "secrets", allowed_handles={handle})


@pytest.mark.parametrize(
    "overrides",
    [
        {"consumer": "../escape"},
        {"keys": {"v1": b"short"}},
        {"active_key_version": "v2"},
        {"keys": {"../v1": b"a" * 32}},
    ],
)
def test_invalid_keyring_or_identity_is_rejected(tmp_path, overrides) -> None:
    from alon_ai.security.secrets import SecretStoreError

    with pytest.raises(SecretStoreError):
        store(tmp_path / "secrets", **overrides)


def test_keyring_and_permissions_are_snapshotted(tmp_path) -> None:
    from alon_ai.security.secrets import SecretStoreError

    allowed = {"api-main"}
    keys = {"v1": b"a" * 32}
    reader = store(tmp_path / "secrets", allowed_handles=allowed, keys=keys)
    allowed.add("api-other")
    keys["v1"] = b"b" * 32
    reader.put("api-main", SecretStr("private-value"))
    assert store(reader.root).get("api-main").get_secret_value() == "private-value"
    with pytest.raises(SecretStoreError):
        reader.put("api-other", SecretStr("private-value"))


@pytest.mark.parametrize(
    "attack", ["wrong-key", "tamper", "swap", "consumer-swap", "key-version"]
)
def test_envelope_authentication_denies_changes_without_exposing_values(
    tmp_path, attack
) -> None:
    from alon_ai.security.secrets import SecretStoreError

    reader = store(tmp_path / "secrets")
    reader.put("api-main", SecretStr("private-value"))
    first = next(reader.root.iterdir())
    if attack == "wrong-key":
        reader = store(reader.root, keys={"v1": b"b" * 32})
    elif attack == "tamper":
        envelope = json.loads(first.read_text())
        envelope["ciphertext"] = "AAAA"
        first.write_text(json.dumps(envelope))
    elif attack == "swap":
        reader.put("api-other", SecretStr("other-value"))
        second = next(path for path in reader.root.iterdir() if path != first)
        first.write_bytes(second.read_bytes())
    elif attack == "consumer-swap":
        other = store(reader.root, consumer="other-adapter")
        other.put("api-main", SecretStr("other-value"))
        second = next(path for path in reader.root.iterdir() if path != first)
        first.write_bytes(second.read_bytes())
    else:
        envelope = json.loads(first.read_text())
        envelope["key_version"] = "v2"
        first.write_text(json.dumps(envelope))
        reader = store(reader.root, keys={"v1": b"a" * 32, "v2": b"a" * 32})
    with pytest.raises(SecretStoreError) as raised:
        reader.get("api-main")
    assert "private-value" not in str(raised.value)
    assert "other-value" not in str(raised.value)
    assert str(tmp_path) not in str(raised.value)


def test_rotation_preserves_access_to_earlier_keys_until_migrated(tmp_path) -> None:
    reader = store(tmp_path / "secrets")
    reader.put("api-main", SecretStr("main-value"))
    reader.put("api-other", SecretStr("other-value"))
    rotated = store(
        reader.root, keys={"v1": b"a" * 32, "v2": b"b" * 32}, active_key_version="v2"
    )
    rotated.rotate("api-main")
    assert rotated.get("api-main").get_secret_value() == "main-value"
    assert rotated.get("api-other").get_secret_value() == "other-value"
    assert (
        store(reader.root, keys={"v2": b"b" * 32}, active_key_version="v2")
        .get("api-main")
        .get_secret_value()
        == "main-value"
    )
    assert {
        json.loads(path.read_text())["key_version"] for path in reader.root.iterdir()
    } == {"v1", "v2"}


@pytest.mark.parametrize(
    "attack",
    [
        "directory-symlink",
        "parent-symlink",
        "file-symlink",
        "hardlink",
        "directory-permissions",
        "file-permissions",
    ],
)
def test_unsafe_filesystem_objects_are_rejected(tmp_path, attack) -> None:
    from alon_ai.security.secrets import SecretStoreError

    root = tmp_path / "secrets"
    reader = store(root)
    reader.put("api-main", SecretStr("private-value"))
    target = next(root.iterdir())
    if attack == "directory-symlink":
        link = tmp_path / "link"
        link.symlink_to(root, target_is_directory=True)
        with pytest.raises(SecretStoreError):
            store(link)
        return
    if attack == "parent-symlink":
        link = tmp_path / "link"
        link.symlink_to(tmp_path, target_is_directory=True)
        with pytest.raises(SecretStoreError):
            store(link / "secrets")
        return
    if attack == "file-symlink":
        outside = tmp_path / "outside"
        target.rename(outside)
        target.symlink_to(outside)
    elif attack == "hardlink":
        os.link(target, tmp_path / "outside")
    elif attack == "directory-permissions":
        root.chmod(0o755)
    else:
        target.chmod(0o644)
    with pytest.raises(SecretStoreError):
        reader.get("api-main")
    with pytest.raises(SecretStoreError):
        reader.put("api-main", SecretStr("replacement-value"))


def test_interrupted_atomic_write_preserves_old_secret_and_cleans_temporary(
    tmp_path, monkeypatch
) -> None:
    from alon_ai.security.secrets import SecretStoreError

    reader = store(tmp_path / "secrets")
    reader.put("api-main", SecretStr("original-value"))

    def fail_replace(*args, **kwargs):
        raise OSError("private-internal-path")

    monkeypatch.setattr(os, "replace", fail_replace)
    with pytest.raises(SecretStoreError) as raised:
        reader.put("api-main", SecretStr("replacement-value"))
    assert "private-internal-path" not in str(raised.value)
    assert reader.get("api-main").get_secret_value() == "original-value"
    assert len(list(reader.root.iterdir())) == 1


@pytest.mark.parametrize("value", ["", "a" * 65537])
def test_empty_and_oversized_secrets_fail_without_writing(tmp_path, value) -> None:
    from alon_ai.security.secrets import SecretStoreError

    reader = store(tmp_path / "secrets")
    with pytest.raises(SecretStoreError):
        reader.put("api-main", SecretStr(value))
    assert not list(reader.root.iterdir())
