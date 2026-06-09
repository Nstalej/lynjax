import type { ReactNode } from 'react';

export type StatusTone = 'stable' | 'watch' | 'alert';

export type StatusCard = {
  label: string;
  value: string;
  detail: string;
  tone: StatusTone;
};

const toneLabels: Record<StatusTone, string> = {
  stable: 'Operativo',
  watch: 'En Observación',
  alert: 'Prioridad Alta',
};

export function StatusCards({ cards }: { cards: StatusCard[] }) {
  if (cards.length === 0) {
    return (
      <section className="status-grid" aria-label="Estado del Assessment">
        <article className="status-card empty-state">
          <p>No hay métricas disponibles todavía.</p>
        </article>
      </section>
    );
  }

  return (
    <section className="status-grid" aria-label="Estado del Assessment">
      {cards.map((card) => (
        <article className={`status-card status-card--${card.tone}`} key={card.label}>
          <div className="status-card__header">
            <p>{card.label}</p>
            <span>{toneLabels[card.tone]}</span>
          </div>
          <strong>{card.value}</strong>
          <small>{card.detail}</small>
        </article>
      ))}
    </section>
  );
}

export function Panel({ title, eyebrow, children }: { title: string; eyebrow: string; children: ReactNode }) {
  return (
    <section className="panel" aria-labelledby={`${title.toLowerCase().replaceAll(' ', '-')}-title`}>
      <p className="eyebrow">{eyebrow}</p>
      <h2 id={`${title.toLowerCase().replaceAll(' ', '-')}-title`}>{title}</h2>
      {children}
    </section>
  );
}
