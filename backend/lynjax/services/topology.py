"""Network topology derived from collected data.

No extra collection happens here. The graph comes from what the connectors
already returned: ARP tells us which addresses answer, MAC tables tell us which
switch port learned them, and default routes tell us which way traffic leaves.

That is the honest limit of it. Without LLDP or CDP, links between infrastructure
devices are inferred from routing rather than observed, so the graph marks how it
knows each edge instead of presenting guesses as facts.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from lynjax.services.audit import NetworkSnapshot, default_route
from lynjax.services.connectors.base import normalize_mac

logger = logging.getLogger("lynjax.topology")

NodeKind = Literal["device", "endpoint", "gateway", "unmanaged"]
EdgeEvidence = Literal["mac-table", "default-route", "arp"]

#: Endpoints beyond this many per switch are summarised rather than drawn. A
#: graph with four hundred laptops on it communicates nothing.
MAX_ENDPOINTS_PER_DEVICE = 12


@dataclass
class Node:
    id: str
    label: str
    kind: NodeKind
    status: str = "unknown"
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    source: str
    target: str
    evidence: EdgeEvidence
    label: str = ""


@dataclass
class Topology:
    nodes: list[Node] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.label,
                    "kind": node.kind,
                    "status": node.status,
                    "detail": node.detail,
                }
                for node in self.nodes
            ],
            "edges": [
                {
                    "source": edge.source,
                    "target": edge.target,
                    "evidence": edge.evidence,
                    "label": edge.label,
                }
                for edge in self.edges
            ],
            "notes": self.notes,
        }


def build_topology(
    snapshot: NetworkSnapshot, *, include_endpoints: bool = True
) -> Topology:
    """Turn a collection snapshot into a graph."""
    topology = Topology()
    seen_nodes: set[str] = set()

    def add_node(node: Node) -> None:
        if node.id not in seen_nodes:
            seen_nodes.add(node.id)
            topology.nodes.append(node)

    by_host = {item.device.host: item for item in snapshot.devices}

    for item in snapshot.devices:
        device = item.device
        add_node(
            Node(
                id=f"device:{device.id}",
                label=device.name,
                kind="device",
                status="offline" if item.error or item.is_empty else device.status,
                detail={
                    "host": device.host,
                    "connector": device.connector_type,
                    "model": item.system_info.get("model", ""),
                    "os_version": item.system_info.get("os_version", ""),
                    "interfaces": len(item.interfaces),
                    "interfaces_down": sum(
                        1 for i in item.interfaces if i.status != "up"
                    ),
                    "error": item.error,
                },
            )
        )

    # Infrastructure links, inferred from default routes.
    for item in snapshot.devices:
        route = default_route(item)
        if route is None or not route.gateway:
            continue

        neighbour = by_host.get(route.gateway)
        if neighbour is not None:
            topology.edges.append(
                Edge(
                    source=f"device:{item.device.id}",
                    target=f"device:{neighbour.device.id}",
                    evidence="default-route",
                    label="default",
                )
            )
            continue

        # A gateway nobody registered still belongs on the map: it is the edge
        # of what we can see, and leaving it off would imply the path ends here.
        gateway_id = f"gateway:{route.gateway}"
        add_node(
            Node(
                id=gateway_id,
                label=route.gateway,
                kind="unmanaged",
                status="unknown",
                detail={
                    "reason": "Not in the inventory; nothing beyond it was checked."
                },
            )
        )
        topology.edges.append(
            Edge(
                source=f"device:{item.device.id}",
                target=gateway_id,
                evidence="default-route",
                label="default",
            )
        )

    if not include_endpoints:
        return topology

    # Endpoints, placed on the switch port that learned their MAC.
    ip_by_mac: dict[str, str] = {}
    for item in snapshot.devices:
        for entry in item.arp:
            if entry.mac and entry.ip:
                ip_by_mac.setdefault(normalize_mac(entry.mac), entry.ip)

    for item in snapshot.devices:
        drawn = 0
        for entry in item.macs:
            mac = normalize_mac(entry.mac)
            if not mac:
                continue

            if drawn >= MAX_ENDPOINTS_PER_DEVICE:
                remaining = len(item.macs) - drawn
                topology.notes.append(
                    f"{item.device.name}: {remaining} more endpoint(s) not drawn, "
                    f"to keep the map readable."
                )
                break

            node_id = f"endpoint:{mac}"
            add_node(
                Node(
                    id=node_id,
                    label=ip_by_mac.get(mac, mac),
                    kind="endpoint",
                    status="online",
                    detail={
                        "mac": mac,
                        "ip": ip_by_mac.get(mac, ""),
                        "port": entry.port,
                    },
                )
            )
            topology.edges.append(
                Edge(
                    source=f"device:{item.device.id}",
                    target=node_id,
                    evidence="mac-table",
                    label=entry.port,
                )
            )
            drawn += 1

    if not any(edge.evidence == "mac-table" for edge in topology.edges):
        topology.notes.append(
            "No MAC address tables were collected, so no endpoint is placed on a "
            "switch port. Add a switch that answers over SSH or SNMP to complete "
            "the map."
        )

    return topology
