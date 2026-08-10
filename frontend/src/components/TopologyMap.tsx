import { useMemo } from 'react';
import type { Topology, TopologyNode } from '../lib/api';

/**
 * Network map.
 *
 * Laid out as rings rather than with a physics simulation: the graphs this draws
 * are tens of nodes, not thousands, and a deterministic layout means the same
 * network looks the same every time — which matters when someone is comparing
 * against what they saw an hour ago.
 *
 * Edge style carries how the link is known. Without LLDP or CDP, links between
 * infrastructure devices are inferred from routing, and drawing an inference the
 * same as an observation would overclaim.
 */

const RING: Record<TopologyNode['kind'], number> = {
  unmanaged: 0,
  device: 1,
  gateway: 1,
  endpoint: 2,
};

const KIND_LABEL: Record<TopologyNode['kind'], string> = {
  device: 'Equipo gestionado',
  endpoint: 'Endpoint',
  gateway: 'Puerta de enlace',
  unmanaged: 'Fuera del inventario',
};

const WIDTH = 900;
const HEIGHT = 460;

export function TopologyMap({ topology }: { topology: Topology }) {
  const positions = useMemo(() => {
    const rings: Record<number, TopologyNode[]> = { 0: [], 1: [], 2: [] };
    for (const node of topology.nodes) {
      rings[RING[node.kind]].push(node);
    }

    const placed = new Map<string, { x: number; y: number }>();
    const centreX = WIDTH / 2;
    const centreY = HEIGHT / 2;

    Object.entries(rings).forEach(([ring, nodes]) => {
      const radius = Number(ring) * 150;
      nodes.forEach((node, index) => {
        if (radius === 0 && nodes.length === 1) {
          placed.set(node.id, { x: centreX, y: centreY });
          return;
        }
        // Offset each ring so nodes do not line up radially and overlap edges.
        const angle =
          (2 * Math.PI * index) / Math.max(nodes.length, 1) + Number(ring) * 0.4;
        placed.set(node.id, {
          x: centreX + radius * Math.cos(angle),
          y: centreY + radius * Math.sin(angle) * 0.72,
        });
      });
    });

    return placed;
  }, [topology]);

  if (topology.nodes.length === 0) {
    return (
      <div className="map map--empty">
        <p className="muted">
          No hay nada que dibujar todavía. Registra dispositivos y ejecuta una
          recolección.
        </p>
        {topology.notes.map((note) => (
          <p className="muted" key={note}>
            {note}
          </p>
        ))}
      </div>
    );
  }

  return (
    <div className="map">
      <svg
        role="img"
        aria-label="Mapa de topología de red"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        {topology.edges.map((edge, index) => {
          const from = positions.get(edge.source);
          const to = positions.get(edge.target);
          if (!from || !to) return null;

          return (
            <g key={`${edge.source}-${edge.target}-${index}`}>
              <line
                className={`map__edge map__edge--${edge.evidence}`}
                x1={from.x}
                y1={from.y}
                x2={to.x}
                y2={to.y}
              />
              {edge.label ? (
                <text
                  className="map__edge-label"
                  x={(from.x + to.x) / 2}
                  y={(from.y + to.y) / 2 - 4}
                  textAnchor="middle"
                >
                  {edge.label}
                </text>
              ) : null}
            </g>
          );
        })}

        {topology.nodes.map((node) => {
          const point = positions.get(node.id);
          if (!point) return null;
          const radius = node.kind === 'endpoint' ? 7 : 14;

          return (
            <g className="map__node" key={node.id}>
              <title>
                {`${KIND_LABEL[node.kind]}: ${node.label}\n${Object.entries(node.detail)
                  .filter(([, value]) => value !== '' && value !== null)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join('\n')}`}
              </title>
              <circle
                className={`map__dot map__dot--${node.kind} map__dot--status-${node.status}`}
                cx={point.x}
                cy={point.y}
                r={radius}
              />
              <text
                className="map__label"
                x={point.x}
                y={point.y + radius + 14}
                textAnchor="middle"
              >
                {node.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="map__legend">
        <span>
          <i className="map__key map__key--device" /> Equipo gestionado
        </span>
        <span>
          <i className="map__key map__key--endpoint" /> Endpoint
        </span>
        <span>
          <i className="map__key map__key--unmanaged" /> Fuera del inventario
        </span>
        <span>
          <i className="map__key map__key--inferred" /> Enlace inferido de rutas
        </span>
      </div>

      {topology.notes.length > 0 ? (
        <ul className="map__notes">
          {topology.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
