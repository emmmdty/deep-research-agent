"""Filesystem registry for versioned YAML domain packs."""

from __future__ import annotations

from pathlib import Path

import yaml

from deep_research_agent.domain_packs.models import DomainPack, DomainPackSummary


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PACKS_DIR = PROJECT_ROOT / "configs" / "domain_packs"


class DomainPackRegistry:
    """Load validated domain packs from one configuration directory."""

    def __init__(self, packs_dir: str | Path = DEFAULT_PACKS_DIR) -> None:
        self._packs_dir = Path(packs_dir)

    def load(self, pack_id: str) -> DomainPack:
        """Load a pack by its declared identifier."""

        if not pack_id or Path(pack_id).name != pack_id:
            raise ValueError("pack_id must be a non-empty file-safe identifier")

        path = self._packs_dir / f"{pack_id}.yaml"
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

        packs = (self.load(path.stem) for path in sorted(self._packs_dir.glob("*.yaml")))
        return [DomainPackSummary.from_pack(pack) for pack in packs]
