"""Candidate representation and constrained enumeration for Pakunoda.

A candidate is a specific decomposition configuration:
which blocks, how modes are assigned (decompose/freeze, common/specific),
and how they couple.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Dict, List, Optional, Set

from pakunoda.graph import RelationGraph


@dataclass
class ModeAssignment:
    """How a single mode in a single block is treated."""
    block: str
    mode: str
    status: str = "decompose"  # "decompose" or "freeze"
    sharing: str = "specific"  # "common" or "specific"

    def to_dict(self):
        return {
            "block": self.block,
            "mode": self.mode,
            "status": self.status,
            "sharing": self.sharing,
        }


@dataclass
class Coupling:
    """A group of modes that are coupled together."""
    group_id: int
    type: str  # "exact" or "nested"
    members: List[Dict] = field(default_factory=list)  # [{"block": ..., "mode": ...}]

    def to_dict(self):
        return {
            "group_id": self.group_id,
            "type": self.type,
            "members": self.members,
        }


@dataclass
class Candidate:
    """A single decomposition candidate."""
    id: str
    blocks: List[str]
    mode_assignments: List[ModeAssignment] = field(default_factory=list)
    couplings: List[Coupling] = field(default_factory=list)
    rank: Optional[int] = None
    solver_family: str = "CoupledMWCA"

    def to_dict(self):
        return {
            "id": self.id,
            "blocks": self.blocks,
            "mode_assignments": [ma.to_dict() for ma in self.mode_assignments],
            "couplings": [c.to_dict() for c in self.couplings],
            "rank": self.rank,
            "solver_family": self.solver_family,
        }


@dataclass
class EnumerationConstraints:
    """Constraints for candidate enumeration."""
    max_blocks: Optional[int] = None
    min_shared_fraction: float = 0.0
    allow_partial_coupling: bool = True
    allow_nested: bool = False
    allow_frozen_modes: bool = False

    @classmethod
    def from_config(cls, config):
        search = config.get("search", {})
        return cls(
            max_blocks=search.get("max_blocks"),
            min_shared_fraction=search.get("min_shared_fraction", 0.0),
            allow_partial_coupling=search.get("allow_partial_coupling", True),
            allow_nested=search.get("allow_nested", False),
            allow_frozen_modes=search.get("allow_frozen_modes", False),
        )


def enumerate_candidates(graph, constraints):
    # type: (RelationGraph, EnumerationConstraints) -> List[Candidate]
    """Enumerate valid decomposition candidates under constraints.

    For each valid block subset (size >= 2):
    1. Find applicable relations
    2. Check constraints (shared fraction, partial coupling, nested)
    3. Build a candidate with standard mode assignments
    4. Optionally add a frozen-mode variant

    Args:
        graph: The relation graph.
        constraints: Enumeration constraints.

    Returns:
        List of valid candidates.
    """
    candidates = []
    block_ids = graph.get_block_ids()
    max_blocks = constraints.max_blocks if constraints.max_blocks else len(block_ids)
    max_blocks = min(max_blocks, len(block_ids))
    candidate_idx = 0

    for size in range(2, max_blocks + 1):
        for subset in combinations(block_ids, size):
            subset_list = list(subset)
            result = _try_build_candidates(
                graph, subset_list, constraints, candidate_idx
            )
            for c in result:
                candidates.append(c)
                candidate_idx += 1

    return candidates


def _try_build_candidates(graph, block_ids, constraints, start_idx):
    # type: (RelationGraph, List[str], EnumerationConstraints, int) -> List[Candidate]
    """Try to build candidates for a given block subset. Returns 0, 1, or 2 candidates."""
    rels = graph.get_relations_for_blocks(block_ids)

    # Filter nested if not allowed
    if not constraints.allow_nested:
        rels = [r for r in rels if r.type != "nested"]

    # Must have at least one relation
    if not rels:
        return []

    # Compute shared fraction
    shared_blocks = set()  # type: Set[str]
    for r in rels:
        for ep in r.endpoints:
            shared_blocks.add(ep.block)
    shared_fraction = len(shared_blocks) / len(block_ids)

    if shared_fraction < constraints.min_shared_fraction:
        return []

    # Check partial coupling
    if not constraints.allow_partial_coupling:
        if shared_blocks != set(block_ids):
            return []

    # Build the standard candidate (all modes decompose)
    candidates = []
    std = _build_standard_candidate(graph, block_ids, rels, start_idx)
    candidates.append(std)

    # Build frozen variant if allowed
    if constraints.allow_frozen_modes:
        frozen = _build_frozen_variant(graph, block_ids, rels, start_idx + 1)
        if frozen:
            candidates.append(frozen)

    return candidates


def _build_standard_candidate(graph, block_ids, rels, idx):
    # type: (RelationGraph, List[str], list, int) -> Candidate
    """Build a candidate where all modes are decomposed."""
    # Determine which mode node ids are coupled
    coupled_ids = set()  # type: Set[str]
    couplings = []
    group_id = 0
    for r in rels:
        members = [{"block": ep.block, "mode": ep.mode} for ep in r.endpoints]
        couplings.append(Coupling(group_id=group_id, type=r.type, members=members))
        for ep in r.endpoints:
            coupled_ids.add(ep.id)
        group_id += 1

    # Build mode assignments
    assignments = []
    for bid in block_ids:
        for m in graph.get_modes_for_block(bid):
            sharing = "common" if m.id in coupled_ids else "specific"
            assignments.append(ModeAssignment(
                block=bid, mode=m.mode, status="decompose", sharing=sharing,
            ))

    tag = "_".join(sorted(block_ids))
    return Candidate(
        id="c{}_{}".format(idx, tag),
        blocks=list(block_ids),
        mode_assignments=assignments,
        couplings=couplings,
    )


def _build_frozen_variant(graph, block_ids, rels, idx):
    # type: (RelationGraph, List[str], list, int) -> Optional[Candidate]
    """Build a variant where all non-shared modes are frozen.

    Returns None if this would be identical to the standard candidate
    (i.e., all modes are already shared).
    """
    coupled_ids = set()  # type: Set[str]
    couplings = []
    group_id = 0
    for r in rels:
        members = [{"block": ep.block, "mode": ep.mode} for ep in r.endpoints]
        couplings.append(Coupling(group_id=group_id, type=r.type, members=members))
        for ep in r.endpoints:
            coupled_ids.add(ep.id)
        group_id += 1

    has_frozen = False
    assignments = []
    for bid in block_ids:
        for m in graph.get_modes_for_block(bid):
            if m.id in coupled_ids:
                assignments.append(ModeAssignment(
                    block=bid, mode=m.mode, status="decompose", sharing="common",
                ))
            else:
                assignments.append(ModeAssignment(
                    block=bid, mode=m.mode, status="freeze", sharing="specific",
                ))
                has_frozen = True

    if not has_frozen:
        return None

    tag = "_".join(sorted(block_ids))
    return Candidate(
        id="c{}_{}_frozen".format(idx, tag),
        blocks=list(block_ids),
        mode_assignments=assignments,
        couplings=couplings,
    )
