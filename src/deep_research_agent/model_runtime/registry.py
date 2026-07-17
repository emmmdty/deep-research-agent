"""Storage-neutral versioned model registry with encrypted credentials."""

from __future__ import annotations

import base64
import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol

import httpx
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from deep_research_agent.model_runtime.models import (
    EndpointCredentialInput,
    JobRuntimeSnapshot,
    ModelCapabilityReport,
    ModelEndpoint,
    ProbeCapabilities,
    ResolutionRecord,
    ResolvedModelEndpoint,
    RuntimeConfigVersion,
)


MASTER_KEY_ENV = "DEEP_RESEARCH_AGENT_MASTER_KEY"


@dataclass(frozen=True)
class EncryptedCredential:
    """AES-GCM ciphertext stored without its master key."""

    nonce: bytes
    ciphertext: bytes


class ModelRegistryStorage(Protocol):
    """Persistence boundary implemented by Task 5 infrastructure."""

    def save_version(self, version: RuntimeConfigVersion) -> None: ...

    def get_version(self, version_id: str) -> RuntimeConfigVersion | None: ...

    def set_active_version_id(self, version_id: str) -> None: ...

    def get_active_version_id(self) -> str | None: ...

    def save_snapshot(self, snapshot: JobRuntimeSnapshot) -> None: ...

    def get_snapshot(self, job_id: str) -> JobRuntimeSnapshot | None: ...

    def save_credential(self, credential_id: str, value: EncryptedCredential) -> None: ...

    def get_credential(self, credential_id: str) -> EncryptedCredential | None: ...

    def record_resolution(self, record: ResolutionRecord) -> None: ...

    def save_capability_report(self, report: ModelCapabilityReport) -> None: ...


class InMemoryModelRegistryStorage:
    """Thread-local-style in-memory adapter for tests and local execution."""

    def __init__(self) -> None:
        self._versions: dict[str, RuntimeConfigVersion] = {}
        self._active_version_id: str | None = None
        self._snapshots: dict[str, JobRuntimeSnapshot] = {}
        self._credentials: dict[str, EncryptedCredential] = {}
        self.resolutions: list[ResolutionRecord] = []
        self.capability_reports: list[ModelCapabilityReport] = []

    def save_version(self, version: RuntimeConfigVersion) -> None:
        existing = self._versions.get(version.version_id)
        if existing is not None and existing != version:
            raise ValueError(f"runtime version {version.version_id!r} already exists")
        self._versions[version.version_id] = version

    def get_version(self, version_id: str) -> RuntimeConfigVersion | None:
        return self._versions.get(version_id)

    def set_active_version_id(self, version_id: str) -> None:
        self._active_version_id = version_id

    def get_active_version_id(self) -> str | None:
        return self._active_version_id

    def save_snapshot(self, snapshot: JobRuntimeSnapshot) -> None:
        existing = self._snapshots.get(snapshot.job_id)
        if existing is not None and existing != snapshot:
            raise ValueError(f"job {snapshot.job_id!r} already has a runtime snapshot")
        self._snapshots[snapshot.job_id] = snapshot

    def get_snapshot(self, job_id: str) -> JobRuntimeSnapshot | None:
        return self._snapshots.get(job_id)

    def save_credential(self, credential_id: str, value: EncryptedCredential) -> None:
        existing = self._credentials.get(credential_id)
        if existing is not None and existing != value:
            raise ValueError(f"credential {credential_id!r} already exists")
        self._credentials[credential_id] = value

    def get_credential(self, credential_id: str) -> EncryptedCredential | None:
        return self._credentials.get(credential_id)

    def record_resolution(self, record: ResolutionRecord) -> None:
        self.resolutions.append(record)

    def save_capability_report(self, report: ModelCapabilityReport) -> None:
        self.capability_reports.append(report)


class CredentialCipher:
    """Encrypts endpoint credentials with an environment-supplied AES-GCM key."""

    def __init__(self, master_key: bytes) -> None:
        if len(master_key) != 32:
            raise ValueError("model credential master key must be exactly 32 bytes")
        self._aes_gcm = AESGCM(master_key)

    @classmethod
    def from_environment(cls, env_var: str = MASTER_KEY_ENV) -> CredentialCipher:
        encoded_key = os.environ.get(env_var)
        if not encoded_key:
            raise ValueError(f"{env_var} must contain a base64-encoded 32-byte key")
        try:
            master_key = base64.b64decode(encoded_key, altchars=b"-_", validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{env_var} must contain a valid base64 key") from exc
        return cls(master_key)

    def encrypt(self, credential_id: str, plaintext: str) -> EncryptedCredential:
        nonce = os.urandom(12)
        ciphertext = self._aes_gcm.encrypt(
            nonce,
            plaintext.encode("utf-8"),
            credential_id.encode("utf-8"),
        )
        return EncryptedCredential(nonce=nonce, ciphertext=ciphertext)

    def decrypt(self, credential_id: str, value: EncryptedCredential) -> str:
        plaintext = self._aes_gcm.decrypt(
            value.nonce,
            value.ciphertext,
            credential_id.encode("utf-8"),
        )
        return plaintext.decode("utf-8")


CapabilityProbe = Callable[[ModelEndpoint], Mapping[str, bool | None] | ProbeCapabilities]


class ModelRegistry:
    """Activates immutable runtime versions and resolves audited fallbacks."""

    def __init__(
        self,
        *,
        storage: ModelRegistryStorage | None = None,
        capability_probe: CapabilityProbe | None = None,
        credential_cipher: CredentialCipher | None = None,
    ) -> None:
        self.storage = storage or InMemoryModelRegistryStorage()
        self._cipher = credential_cipher or CredentialCipher.from_environment()
        self._capability_probe = capability_probe

    def register(
        self,
        version: RuntimeConfigVersion,
        *,
        credentials: Iterable[EndpointCredentialInput] = (),
    ) -> None:
        credentials_by_id: dict[str, EndpointCredentialInput] = {}
        for credential in credentials:
            if credential.credential_id in credentials_by_id:
                raise ValueError(f"duplicate credential input {credential.credential_id!r}")
            credentials_by_id[credential.credential_id] = credential

        required_ids = {endpoint.credential_id for endpoint in version.endpoints}
        supplied_or_stored_ids = set(credentials_by_id)
        supplied_or_stored_ids.update(
            credential_id
            for credential_id in required_ids
            if self.storage.get_credential(credential_id) is not None
        )
        missing = required_ids - supplied_or_stored_ids
        if missing:
            raise ValueError(f"missing endpoint credentials: {', '.join(sorted(missing))}")

        self.storage.save_version(version)
        for credential_id, credential in credentials_by_id.items():
            encrypted = self._cipher.encrypt(
                credential_id,
                credential.api_key.get_secret_value(),
            )
            self.storage.save_credential(credential_id, encrypted)

    def activate(self, version_id: str) -> RuntimeConfigVersion:
        version = self.storage.get_version(version_id)
        if version is None:
            raise KeyError(f"unknown runtime version: {version_id}")
        self.storage.set_active_version_id(version_id)
        return version

    def snapshot_for_job(self, job_id: str) -> JobRuntimeSnapshot:
        existing = self.storage.get_snapshot(job_id)
        if existing is not None:
            return existing
        version = self._active_version()
        snapshot = JobRuntimeSnapshot(
            job_id=job_id,
            version=version,
            fallback_chains={
                profile.role: tuple(profile.endpoint_ids) for profile in version.role_profiles
            },
        )
        self.storage.save_snapshot(snapshot)
        return snapshot

    def resolve(
        self,
        role: str,
        attempt: int,
        *,
        job_id: str,
    ) -> ResolvedModelEndpoint:
        snapshot = self.snapshot_for_job(job_id)
        try:
            chain = snapshot.fallback_chains[role]
        except KeyError as exc:
            raise KeyError(f"unknown model role: {role}") from exc
        resolved = self._resolve_from_version(snapshot.version, role, attempt, chain)
        self.storage.record_resolution(
            ResolutionRecord(
                version_id=snapshot.version.version_id,
                job_id=job_id,
                role=role,
                attempt=attempt,
                endpoint_id=resolved.endpoint_id,
                model=resolved.model,
            )
        )
        return resolved

    def preview_active(self, role: str, attempt: int) -> ResolvedModelEndpoint:
        """Preview active routing for administrators without recording execution."""

        version = self._active_version()
        chain = self._chain_for_role(version, role)
        return self._resolve_from_version(version, role, attempt, chain)

    def probe(self, endpoint_id: str) -> ModelCapabilityReport:
        endpoint = self._find_endpoint(self._active_version(), endpoint_id)
        try:
            capabilities = (
                self._capability_probe(endpoint)
                if self._capability_probe is not None
                else self._probe_over_http(endpoint)
            )
            normalized = ProbeCapabilities.model_validate(capabilities)
            if not normalized.model_available:
                raise LookupError(
                    f"configured model {endpoint.model!r} is unavailable at endpoint"
                )
            report = ModelCapabilityReport(
                endpoint_id=endpoint.endpoint_id,
                model=endpoint.model,
                ok=True,
                model_available=True,
                declared_supports_structured_output=endpoint.supports_structured_output,
                declared_supports_tool_use=endpoint.supports_tool_use,
                verified_supports_structured_output=(
                    normalized.verified_supports_structured_output
                ),
                verified_supports_tool_use=normalized.verified_supports_tool_use,
            )
        except Exception as exc:
            report = ModelCapabilityReport(
                endpoint_id=endpoint.endpoint_id,
                model=endpoint.model,
                ok=False,
                model_available=False,
                declared_supports_structured_output=endpoint.supports_structured_output,
                declared_supports_tool_use=endpoint.supports_tool_use,
                error=str(exc) or type(exc).__name__,
            )
        self.storage.save_capability_report(report)
        return report

    def _active_version(self) -> RuntimeConfigVersion:
        version_id = self.storage.get_active_version_id()
        if version_id is None:
            raise RuntimeError("no runtime configuration is active")
        version = self.storage.get_version(version_id)
        if version is None:
            raise RuntimeError(f"active runtime version {version_id!r} is unavailable")
        return version

    @staticmethod
    def _chain_for_role(version: RuntimeConfigVersion, role: str) -> tuple[str, ...]:
        for profile in version.role_profiles:
            if profile.role == role:
                return profile.endpoint_ids
        raise KeyError(f"unknown model role: {role}")

    @staticmethod
    def _find_endpoint(version: RuntimeConfigVersion, endpoint_id: str) -> ModelEndpoint:
        for endpoint in version.endpoints:
            if endpoint.endpoint_id == endpoint_id:
                return endpoint
        raise KeyError(f"unknown model endpoint: {endpoint_id}")

    @classmethod
    def _resolve_from_version(
        cls,
        version: RuntimeConfigVersion,
        role: str,
        attempt: int,
        chain: tuple[str, ...],
    ) -> ResolvedModelEndpoint:
        if attempt < 0:
            raise ValueError("attempt must be non-negative")
        if attempt >= len(chain):
            raise LookupError(f"fallback chain exhausted for role {role!r} at attempt {attempt}")
        endpoint = cls._find_endpoint(version, chain[attempt])
        return ResolvedModelEndpoint(
            version_id=version.version_id,
            role=role,
            attempt=attempt,
            endpoint_id=endpoint.endpoint_id,
            base_url=endpoint.base_url,
            model=endpoint.model,
            credential_id=endpoint.credential_id,
            tier=endpoint.tier,
            timeout_seconds=endpoint.timeout_seconds,
            supports_structured_output=endpoint.supports_structured_output,
            supports_tool_use=endpoint.supports_tool_use,
        )

    def _api_key_for_client(self, credential_id: str) -> str:
        encrypted = self.storage.get_credential(credential_id)
        if encrypted is None:
            raise KeyError(f"unknown endpoint credential: {credential_id}")
        return self._cipher.decrypt(credential_id, encrypted)

    def _probe_over_http(self, endpoint: ModelEndpoint) -> ProbeCapabilities:
        api_key = self._api_key_for_client(endpoint.credential_id)
        url = f"{str(endpoint.base_url).rstrip('/')}/models"
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=endpoint.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("model capability probe returned an invalid /models payload")
        model_ids = {
            item.get("id")
            for item in payload["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if endpoint.model not in model_ids:
            raise LookupError(
                f"configured model {endpoint.model!r} is absent from the /models response"
            )
        return ProbeCapabilities(model_available=True)
