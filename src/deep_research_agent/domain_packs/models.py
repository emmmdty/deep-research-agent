"""Typed models for declarative research domain packs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Domain-pack model that rejects undeclared configuration fields."""

    model_config = ConfigDict(extra="forbid")


class DomainRelation(StrictModel):
    """One declarative relation permitted by a domain pack."""

    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    source_types: list[str] = Field(min_length=1)
    target_types: list[str] = Field(min_length=1)


class DomainPack(StrictModel):
    """Versioned research vocabulary and suggested investigation surface."""

    schema_version: Literal["1.0"]
    pack_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    entity_types: list[str] = Field(min_length=1)
    relations: list[DomainRelation] = Field(default_factory=list)
    research_questions: list[str] = Field(min_length=1)
    source_types: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_vocabulary(self) -> DomainPack:
        if len(self.entity_types) != len(set(self.entity_types)):
            raise ValueError("domain entity types must be unique")
        if len(self.source_types) != len(set(self.source_types)):
            raise ValueError("domain source types must be unique")

        relation_names = [relation.name for relation in self.relations]
        if len(relation_names) != len(set(relation_names)):
            raise ValueError("domain relation names must be unique")

        known_entities = set(self.entity_types)
        for relation in self.relations:
            referenced_entities = set(relation.source_types) | set(relation.target_types)
            unknown_entities = referenced_entities - known_entities
            if unknown_entities:
                unknown = ", ".join(sorted(unknown_entities))
                raise ValueError(f"relation {relation.name!r} references unknown entity types: {unknown}")
        return self


class DomainPackSummary(StrictModel):
    """Stable projection returned when available packs are listed."""

    pack_id: str
    version: str
    title: str
    description: str

    @classmethod
    def from_pack(cls, pack: DomainPack) -> DomainPackSummary:
        return cls(
            pack_id=pack.pack_id,
            version=pack.version,
            title=pack.title,
            description=pack.description,
        )
