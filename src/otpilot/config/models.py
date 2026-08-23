"""Non-secret application configuration."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = "gmail"
    account: str | None = None


class CredentialBackendConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    backend: str = "windows-credential-manager"


class AppConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    credential_backend: CredentialBackendConfig = Field(default_factory=CredentialBackendConfig)
    config_dir: Path | None = None
    poll_interval_seconds: float = Field(default=30.0, gt=0, le=3600)
