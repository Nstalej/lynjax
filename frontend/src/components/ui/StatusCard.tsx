import { StatusBadge } from './StatusBadge';
import type { StatusTone } from '../../types/platform';

export function StatusCard({
  label,
  value,
  detail,
  tone = 'neutral',
  status,
}: {
  label: string;
  value: string;
  detail: string;
  tone?: StatusTone;
  status: string;
}) {
  return (
    <article className={`status-card status-card--${tone}`}>
      <div className="status-card__header">
        <p>{label}</p>
        <StatusBadge tone={tone}>{status}</StatusBadge>
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </article>
  );
}
