from __future__ import annotations

import base64

import pytest
from pydantic import ValidationError
from pytest_httpx import HTTPXMock

from deep_research_agent.model_runtime.client import OpenAICompatibleClientFactory
from deep_research_agent.model_runtime.models import (
    AgentRoleProfile,
    EndpointCredentialInput,
    ModelEndpoint,
    RuntimeConfigVersion,
)
from deep_research_agent.model_runtime.registry import (
    MASTER_KEY_ENV,
    InMemoryModelRegistryStorage,
    ModelRegistry,
)


def _endpoint(
    endpoint_id: str,
    *,
    model: str,
    tier: str = "quality",
    structured_output: bool = True,
    tool_use: bool = True,
) -> ModelEndpoint:
    return ModelEndpoint(
        endpoint_id=endpoint_id,
        base_url=f"https://{endpoint_id}.example.test/v1",
        model=model,
        credential_id=f"credential:{endpoint_id}",
        tier=tier,
        timeout_seconds=12.5,
        supports_structured_output=structured_output,
        supports_tool_use=tool_use,
    )


def _version(version_id: str = "runtime-v1") -> RuntimeConfigVersion:
    return RuntimeConfigVersion(
        version_id=version_id,
        endpoints=(
            _endpoint("planner-primary", model="planner-large"),
            _endpoint("planner-fallback", model="planner-medium"),
            _endpoint("extractor-primary", model="extractor-json", tier="fast"),
        ),
        role_profiles=(
            AgentRoleProfile(
                role="planner",
                tier="quality",
                endpoint_ids=("planner-primary", "planner-fallback"),
            ),
            AgentRoleProfile(
                role="extractor",
                tier="fast",
                endpoint_ids=("extractor-primary",),
            ),
        ),
    )


def _credentials() -> tuple[EndpointCredentialInput, ...]:
    return (
        EndpointCredentialInput(
            credential_id="credential:planner-primary",
            api_key="planner-primary-secret",
        ),
        EndpointCredentialInput(
            credential_id="credential:planner-fallback",
            api_key="planner-fallback-secret",
        ),
        EndpointCredentialInput(
            credential_id="credential:extractor-primary",
            api_key="extractor-secret",
        ),
    )


@pytest.fixture
def registry(monkeypatch: pytest.MonkeyPatch) -> ModelRegistry:
    master_key = base64.urlsafe_b64encode(b"k" * 32).decode("ascii")
    monkeypatch.setenv(MASTER_KEY_ENV, master_key)
    model_registry = ModelRegistry(storage=InMemoryModelRegistryStorage())
    model_registry.register(_version(), credentials=_credentials())
    model_registry.activate("runtime-v1")
    return model_registry


def test_registry_selects_independent_endpoint_and_model_per_role(registry: ModelRegistry) -> None:
    planner = registry.resolve("planner", 0, job_id="job-roles")
    extractor = registry.resolve("extractor", 0, job_id="job-roles")

    assert (planner.endpoint_id, planner.model) == ("planner-primary", "planner-large")
    assert (extractor.endpoint_id, extractor.model) == (
        "extractor-primary",
        "extractor-json",
    )
    assert planner.base_url != extractor.base_url
    assert planner.credential_id != extractor.credential_id


def test_job_snapshot_and_fallback_chain_remain_immutable_after_activation(
    registry: ModelRegistry,
) -> None:
    snapshot = registry.snapshot_for_job("job-1")
    registry.register(
        RuntimeConfigVersion(
            version_id="runtime-v2",
            endpoints=(_endpoint("planner-new", model="planner-next"),),
            role_profiles=(
                AgentRoleProfile(
                    role="planner",
                    tier="quality",
                    endpoint_ids=("planner-new",),
                ),
            ),
        ),
        credentials=(
            EndpointCredentialInput(
                credential_id="credential:planner-new",
                api_key="new-secret",
            ),
        ),
    )
    registry.activate("runtime-v2")

    assert registry.snapshot_for_job("job-1") == snapshot
    assert registry.resolve("planner", 0, job_id="job-1").endpoint_id == "planner-primary"
    assert registry.resolve("planner", 1, job_id="job-1").endpoint_id == "planner-fallback"
    assert registry.preview_active("planner", 0).endpoint_id == "planner-new"
    assert '"planner":["planner-primary","planner-fallback"]' in snapshot.model_dump_json()
    with pytest.raises(TypeError):
        snapshot.fallback_chains["planner"] = ("planner-new",)


def test_registry_uses_only_ordered_same_tier_fallbacks(registry: ModelRegistry) -> None:
    fallback = registry.resolve("planner", 1, job_id="job-fallback")

    assert (fallback.endpoint_id, fallback.model, fallback.attempt) == (
        "planner-fallback",
        "planner-medium",
        1,
    )
    with pytest.raises(LookupError, match="fallback chain exhausted"):
        registry.resolve("planner", 2, job_id="job-fallback")

    with pytest.raises(ValidationError, match="same tier"):
        RuntimeConfigVersion(
            version_id="invalid-cross-tier",
            endpoints=(
                _endpoint("quality", model="quality-model"),
                _endpoint("cheap", model="cheap-model", tier="economy"),
            ),
            role_profiles=(
                AgentRoleProfile(
                    role="planner",
                    tier="quality",
                    endpoint_ids=("quality", "cheap"),
                ),
            ),
        )


def test_failed_capability_probe_returns_a_failure_report_without_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MASTER_KEY_ENV, base64.urlsafe_b64encode(b"p" * 32).decode())

    def fail_probe(_endpoint: ModelEndpoint) -> dict[str, bool]:
        raise TimeoutError("provider did not respond")

    registry = ModelRegistry(
        storage=InMemoryModelRegistryStorage(),
        capability_probe=fail_probe,
    )
    registry.register(_version(), credentials=_credentials())
    registry.activate("runtime-v1")

    report = registry.probe("planner-primary")

    assert report.ok is False
    assert report.error == "provider did not respond"
    assert report.model_available is False
    assert report.declared_supports_structured_output is True
    assert report.declared_supports_tool_use is True
    assert report.verified_supports_structured_output is None
    assert report.verified_supports_tool_use is None
    assert "secret" not in report.model_dump_json()


def test_default_probe_verifies_model_without_echoing_declared_capabilities(
    registry: ModelRegistry,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://planner-primary.example.test/v1/models",
        match_headers={"Authorization": "Bearer planner-primary-secret"},
        json={"data": [{"id": "planner-large"}, {"id": "another-model"}]},
    )

    report = registry.probe("planner-primary")

    assert report.ok is True
    assert report.model_available is True
    assert report.declared_supports_structured_output is True
    assert report.declared_supports_tool_use is True
    assert report.verified_supports_structured_output is None
    assert report.verified_supports_tool_use is None


def test_default_probe_fails_when_configured_model_is_absent(
    registry: ModelRegistry,
    httpx_mock: HTTPXMock,
) -> None:
    httpx_mock.add_response(
        url="https://planner-primary.example.test/v1/models",
        json={"data": [{"id": "different-model"}]},
    )

    report = registry.probe("planner-primary")

    assert report.ok is False
    assert report.model_available is False
    assert "planner-large" in (report.error or "")
    assert report.verified_supports_structured_output is None
    assert report.verified_supports_tool_use is None


def test_custom_active_probe_can_report_verified_capabilities(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MASTER_KEY_ENV, base64.urlsafe_b64encode(b"v" * 32).decode())

    def active_probe(_endpoint: ModelEndpoint) -> dict[str, bool]:
        return {
            "model_available": True,
            "verified_supports_structured_output": True,
            "verified_supports_tool_use": False,
        }

    registry = ModelRegistry(
        storage=InMemoryModelRegistryStorage(),
        capability_probe=active_probe,
    )
    registry.register(_version(), credentials=_credentials())
    registry.activate("runtime-v1")

    report = registry.probe("planner-primary")

    assert report.ok is True
    assert report.model_available is True
    assert report.verified_supports_structured_output is True
    assert report.verified_supports_tool_use is False


def test_credentials_are_write_only_redacted_and_encrypted_at_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MASTER_KEY_ENV, base64.urlsafe_b64encode(b"s" * 32).decode())
    storage = InMemoryModelRegistryStorage()
    registry = ModelRegistry(storage=storage)
    credential = EndpointCredentialInput(
        credential_id="credential:planner-primary",
        api_key="never-serialize-this-secret",
    )

    assert credential.model_dump() == {"credential_id": "credential:planner-primary"}
    assert "never-serialize-this-secret" not in repr(credential)
    assert "never-serialize-this-secret" not in credential.model_dump_json()

    registry.register(_version(), credentials=(credential, *_credentials()[1:]))
    encrypted = storage.get_credential("credential:planner-primary")

    assert encrypted is not None
    assert b"never-serialize-this-secret" not in encrypted.ciphertext
    assert "never-serialize-this-secret" not in repr(encrypted)


def test_client_factory_uses_each_resolved_endpoint_capabilities_and_secret(
    registry: ModelRegistry,
) -> None:
    built: list[dict[str, object]] = []

    def build_client(**settings: object) -> object:
        built.append(settings)
        return object()

    factory = OpenAICompatibleClientFactory(registry=registry, model_builder=build_client)
    planner_client = factory.create(registry.resolve("planner", 0, job_id="job-client"))
    extractor_client = factory.create(registry.resolve("extractor", 0, job_id="job-client"))

    assert planner_client.endpoint_id == "planner-primary"
    assert planner_client.model_name == "planner-large"
    assert planner_client.supports_structured_output is True
    assert planner_client.supports_tool_use is True
    assert extractor_client.endpoint_id == "extractor-primary"
    assert built == [
        {
            "base_url": "https://planner-primary.example.test/v1",
            "model": "planner-large",
            "api_key": "planner-primary-secret",
            "timeout_seconds": 12.5,
            "supports_structured_output": True,
            "supports_tool_use": True,
        },
        {
            "base_url": "https://extractor-primary.example.test/v1",
            "model": "extractor-json",
            "api_key": "extractor-secret",
            "timeout_seconds": 12.5,
            "supports_structured_output": True,
            "supports_tool_use": True,
        },
    ]


def test_environment_master_key_must_decode_to_exactly_32_bytes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(MASTER_KEY_ENV, base64.urlsafe_b64encode(b"short").decode())

    with pytest.raises(ValueError, match="32 bytes"):
        ModelRegistry(storage=InMemoryModelRegistryStorage())


def test_operational_resolution_requires_job_id_and_admin_preview_is_separate(
    registry: ModelRegistry,
) -> None:
    with pytest.raises(TypeError):
        registry.resolve("planner", 0)

    preview = registry.preview_active("planner", 0)

    assert (preview.endpoint_id, preview.version_id) == ("planner-primary", "runtime-v1")
