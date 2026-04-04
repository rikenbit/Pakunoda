"""Typed relation graph for Pakunoda.

Lightweight dataclass representation of the block-mode relation graph.
Used by candidate enumeration and compilation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class ModeNode:
    """A single mode within a block."""
    block: str
    mode: str
    dimension: Optional[int] = None

    @property
    def id(self):
        return "{}:{}".format(self.block, self.mode)


@dataclass
class Relation:
    """A relation between two or more modes across blocks."""
    type: str  # "exact" or "nested"
    endpoints: List[ModeNode] = field(default_factory=list)
    mapping: Optional[str] = None


@dataclass
class RelationGraph:
    """The block-mode relation graph.

    Holds blocks, modes, relations, and provides query methods
    for candidate enumeration.
    """
    blocks: List[Dict]  # block definitions from config
    modes: List[ModeNode] = field(default_factory=list)
    relations: List[Relation] = field(default_factory=list)

    @classmethod
    def from_config(cls, config, block_metadata=None):
        """Build a RelationGraph from a validated config dict.

        Args:
            config: Validated Pakunoda config.
            block_metadata: Optional dict mapping block_id -> metadata with 'shape'.
        """
        if block_metadata is None:
            block_metadata = {}

        blocks = config.get("blocks", [])
        modes = []
        for block in blocks:
            bid = block["id"]
            meta = block_metadata.get(bid, {})
            shape = meta.get("shape", [])
            for i, mode_name in enumerate(block["modes"]):
                dim = shape[i] if i < len(shape) else None
                modes.append(ModeNode(block=bid, mode=mode_name, dimension=dim))

        relations = []
        for rel in config.get("relations", []):
            endpoints = []
            for ep in rel["between"]:
                # Find dimension from modes we already built
                node = _find_mode(modes, ep["block"], ep["mode"])
                endpoints.append(node if node else ModeNode(block=ep["block"], mode=ep["mode"]))
            relations.append(Relation(
                type=rel["type"],
                endpoints=endpoints,
                mapping=rel.get("mapping"),
            ))

        return cls(blocks=blocks, modes=modes, relations=relations)

    @classmethod
    def from_graph_json(cls, config, graph_dict):
        """Build from the existing graph JSON (output of graph rule)."""
        blocks = config.get("blocks", [])
        node_map = {}
        modes = []
        for n in graph_dict.get("nodes", []):
            mn = ModeNode(block=n["block"], mode=n["mode"], dimension=n.get("dimension"))
            modes.append(mn)
            node_map[n["id"]] = mn

        relations = []
        for e in graph_dict.get("edges", []):
            src = node_map.get(e["source"])
            dst = node_map.get(e["target"])
            if src and dst:
                relations.append(Relation(
                    type=e["type"],
                    endpoints=[src, dst],
                    mapping=e.get("mapping"),
                ))

        return cls(blocks=blocks, modes=modes, relations=relations)

    def get_block_ids(self):
        # type: () -> List[str]
        return [b["id"] for b in self.blocks]

    def get_modes_for_block(self, block_id):
        # type: (str) -> List[ModeNode]
        return [m for m in self.modes if m.block == block_id]

    def get_relations_for_blocks(self, block_ids):
        # type: (List[str]) -> List[Relation]
        """Return relations where ALL endpoints are in the given block set."""
        block_set = set(block_ids)
        return [
            r for r in self.relations
            if all(ep.block in block_set for ep in r.endpoints)
        ]

    def get_shared_block_ids(self, block_ids):
        # type: (List[str]) -> Set[str]
        """Block ids that participate in at least one relation within the subset."""
        rels = self.get_relations_for_blocks(block_ids)
        shared = set()  # type: Set[str]
        for r in rels:
            for ep in r.endpoints:
                shared.add(ep.block)
        return shared

    def get_coupled_modes(self, block_ids):
        # type: (List[str]) -> List[Set[str]]
        """Return groups of mode node ids coupled by exact relations (union-find)."""
        rels = self.get_relations_for_blocks(block_ids)
        exact_rels = [r for r in rels if r.type == "exact"]
        if not exact_rels:
            return []

        # Collect all mode ids involved
        all_ids = set()  # type: Set[str]
        for r in exact_rels:
            for ep in r.endpoints:
                all_ids.add(ep.id)

        # Union-find
        parent = {mid: mid for mid in all_ids}

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a, b):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for r in exact_rels:
            ids = [ep.id for ep in r.endpoints]
            for i in range(1, len(ids)):
                union(ids[0], ids[i])

        groups = {}  # type: Dict[str, Set[str]]
        for mid in all_ids:
            root = find(mid)
            if root not in groups:
                groups[root] = set()
            groups[root].add(mid)

        return [g for g in groups.values() if len(g) > 1]


def _find_mode(modes, block, mode_name):
    # type: (List[ModeNode], str, str) -> Optional[ModeNode]
    for m in modes:
        if m.block == block and m.mode == mode_name:
            return m
    return None
