"""Consumer-scoped AES-256-GCM envelopes with externally supplied versioned keys.

Trusted composition constructs separate stores for each consumer. Consumers receive
only SecretStore; provisioning owns put/rotate and the keyring. This boundary does
not isolate hostile Python in the same process or other processes under the same UID.
"""

import base64
import hashlib
import json
import os
import re
import secrets
import stat
from collections.abc import Collection, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import Protocol

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

_ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", re.ASCII)
_MAX_SECRET_BYTES = 65536
_MAX_ENVELOPE_BYTES = 100000


class SecretStoreError(Exception):
    """A redacted access/storage failure; contains no secret, path or envelope."""


class SecretStore(Protocol):
    def get(self, handle: str) -> SecretStr:
        """Resolve an opaque handle under the consumer's preassigned authority."""
        ...


def _valid_id(value: str) -> bool:
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def _deny() -> SecretStoreError:
    return SecretStoreError("Secret access failed")


class EncryptedFileSecretStore:
    def __init__(
        self,
        root: Path,
        *,
        consumer: str,
        allowed_handles: Collection[str],
        keys: Mapping[str, bytes],
        active_key_version: str,
    ) -> None:
        if (
            not _valid_id(consumer)
            or not _valid_id(active_key_version)
            or active_key_version not in keys
            or not all(_valid_id(handle) for handle in allowed_handles)
            or not all(
                _valid_id(version) and isinstance(key, bytes) and len(key) == 32
                for version, key in keys.items()
            )
        ):
            raise _deny()
        self.root = Path(root).absolute()
        if ".." in self.root.parts:
            raise _deny()
        self._consumer = consumer
        self._allowed_handles = frozenset(allowed_handles)
        self._keys = MappingProxyType(dict(keys))
        self._active_key_version = active_key_version
        try:
            with self._directory(create=True):
                pass
        except (OSError, ValueError, TypeError, KeyError, InvalidTag, SecretStoreError):
            raise _deny() from None

    @contextmanager
    def _directory(self, *, create: bool = False) -> Iterator[int]:
        # Walk from / using directory descriptors; reject symlinked ancestors too.
        fd = os.open(self.root.anchor, os.O_RDONLY | os.O_DIRECTORY)
        try:
            for index, part in enumerate(self.root.parts[1:]):
                last = index == len(self.root.parts) - 2
                if create and last:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=fd)
                    except FileExistsError:
                        pass
                next_fd = os.open(
                    part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd
                )
                os.close(fd)
                fd = next_fd
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise _deny()
            yield fd
        finally:
            os.close(fd)

    def _filename(self, handle: str) -> str:
        if not _valid_id(handle) or handle not in self._allowed_handles:
            raise _deny()
        return (
            hashlib.sha256(json.dumps([self._consumer, handle]).encode()).hexdigest()
            + ".json"
        )

    def _aad(self, handle: str, key_version: str) -> bytes:
        return json.dumps(
            ["alon-ai-secret", 1, self._consumer, handle, key_version],
            separators=(",", ":"),
        ).encode()

    def _read(self, directory: int, filename: str) -> bytes:
        fd = os.open(
            filename, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        try:
            info = os.fstat(fd)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1
                or info.st_size > _MAX_ENVELOPE_BYTES
            ):
                raise _deny()
            with os.fdopen(fd, "rb", closefd=False) as stream:
                value = stream.read(_MAX_ENVELOPE_BYTES + 1)
            if len(value) > _MAX_ENVELOPE_BYTES:
                raise _deny()
            return value
        finally:
            os.close(fd)

    def get(self, handle: str) -> SecretStr:
        try:
            filename = self._filename(handle)
            with self._directory() as directory:
                envelope = json.loads(self._read(directory, filename))
            if (
                set(envelope)
                != {
                    "version",
                    "key_version",
                    "key_nonce",
                    "wrapped_key",
                    "nonce",
                    "ciphertext",
                }
                or envelope["version"] != 1
            ):
                raise _deny()
            version = envelope["key_version"]
            if not _valid_id(version):
                raise _deny()
            aad = self._aad(handle, version)
            key_nonce, wrapped_key, nonce, ciphertext = (
                base64.b64decode(envelope[field], validate=True)
                for field in ("key_nonce", "wrapped_key", "nonce", "ciphertext")
            )
            if len(key_nonce) != 12 or len(nonce) != 12:
                raise _deny()
            data_key = AESGCM(self._keys[version]).decrypt(key_nonce, wrapped_key, aad)
            value = AESGCM(data_key).decrypt(nonce, ciphertext, aad)
            if not value or len(value) > _MAX_SECRET_BYTES:
                raise _deny()
            return SecretStr(value.decode("utf-8"))
        except (OSError, ValueError, TypeError, KeyError, InvalidTag, SecretStoreError):
            raise _deny() from None

    def put(self, handle: str, value: SecretStr) -> None:
        """Provision a handle atomically using the active externally supplied key."""
        try:
            filename = self._filename(handle)
            if not isinstance(value, SecretStr):
                raise _deny()
            plaintext = value.get_secret_value().encode("utf-8")
            if not plaintext or len(plaintext) > _MAX_SECRET_BYTES:
                raise _deny()
            version = self._active_key_version
            aad = self._aad(handle, version)
            data_key = AESGCM.generate_key(bit_length=256)
            key_nonce, nonce = secrets.token_bytes(12), secrets.token_bytes(12)
            envelope = {
                "version": 1,
                "key_version": version,
                **{
                    name: base64.b64encode(data).decode("ascii")
                    for name, data in {
                        "key_nonce": key_nonce,
                        "wrapped_key": AESGCM(self._keys[version]).encrypt(
                            key_nonce, data_key, aad
                        ),
                        "nonce": nonce,
                        "ciphertext": AESGCM(data_key).encrypt(nonce, plaintext, aad),
                    }.items()
                },
            }
            with self._directory() as directory:
                try:
                    self._read(directory, filename)
                except FileNotFoundError:
                    pass
                temporary = "." + secrets.token_hex(16) + ".tmp"
                fd = os.open(
                    temporary,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    0o600,
                    dir_fd=directory,
                )
                try:
                    with os.fdopen(fd, "w", closefd=False) as stream:
                        json.dump(envelope, stream, separators=(",", ":"))
                        stream.flush()
                        os.fsync(fd)
                    os.replace(
                        temporary, filename, src_dir_fd=directory, dst_dir_fd=directory
                    )
                    os.fsync(directory)
                finally:
                    os.close(fd)
                    try:
                        os.unlink(temporary, dir_fd=directory)
                    except FileNotFoundError:
                        pass
        except (OSError, ValueError, TypeError, KeyError, InvalidTag, SecretStoreError):
            raise _deny() from None

    def rotate(self, handle: str) -> None:
        """Re-encrypt one authorized handle; retain old keys until all migrate.

        Provisioning and rotation must be serialized by the trusted operator. A
        failed write preserves the old envelope; other handles remain readable
        with their original versions in the copied keyring.
        """
        self.put(handle, self.get(handle))
