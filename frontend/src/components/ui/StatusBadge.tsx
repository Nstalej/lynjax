import type { ReactNode } from 'react';
import type { StatusTone } from '../../types/platform';

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: StatusTone }) {
  return <span className={`status-badge status-badge--${tone}`}>{children}</span>;
}
