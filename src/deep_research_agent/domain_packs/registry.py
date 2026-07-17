"""Filesystem registry for versioned YAML domain packs."""

from __future__ import annotations

from importlib.abc import Traversable
from importlib import resources
from pathlib import Path

import yaml

from deep_research_agent.domain_packs.models import DomainPack, DomainPackSummary


DOMAIN_PACK_PACKAGE = "deep_research_agent.domain_packs"


class DomainPackRegistry:
    """Load validated domain packs from one configuration directory."""

    def __init__(self, packs_dir: str | Path | None = None) -> None:
        self._packs_dir = Path(packs_dir) if packs_dir is not None else None

    def _root(self) -> Traversable:
        if self._packs_dir is not None:
            return self._packs_dir
        return resources.files(DOMAIN_PACK_PACKAGE).joinpath("packs")

    def load(self, pack_id: str) -> DomainPack:
        """Load a pack by its declared identifier."""

        if not pack_id or Path(pack_id).name != pack_id:
            raise ValueError("pack_id must be a non-empty file-safe identifier")

        path = self._root().joinpath(f"{pack_id}.yaml")
        if not path.is_file():
            raise KeyError(f"unknown domain pack: {pack_id}")

        with path.open("r", encoding="utf-8") as stream:
            payload = yaml.safe_load(stream)
        pack = DomainPack.model_validate(payload)
        if pack.pack_id != pack_id:
            raise ValueError(
                f"domain pack filename {pack_id!r} does not match declared id {pack.pack_id!r}"
            )
        return pack

    def list(self) -> list[DomainPackSummary]:
        """List all valid packs in deterministic identifier order."""

        pack_ids = sorted(
            path.name.removesuffix(".yaml")
            for path in self._root().iterdir()
            if path.is_file() and path.name.endswith(".yaml")
        )
        return [DomainPackSummary.from_pack(self.load(pack_id)) for pack_id in pack_ids]
