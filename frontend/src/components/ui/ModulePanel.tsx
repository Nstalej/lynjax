import type { ReactNode } from 'react';
import type { ModuleStatus } from '../../types/platform';
import { StatusBadge } from './StatusBadge';

const statusTone: Record<ModuleStatus, 'stable' | 'watch' | 'alert' | 'neutral'> = {
  active: 'stable',
  ready: 'stable',
  planned: 'watch',
  readonly: 'neutral',
};

export function ModulePanel({
  title,
  eyebrow,
  body,
  status = 'ready',
  metadata,
  children,
}: {
  title: string;
  eyebrow?: string;
  body?: string;
  status?: ModuleStatus;
  metadata?: string;
  children?: ReactNode;
}) {
  return (
    <article className="module-panel">
      <div className="module-panel__header">
        <div>
          {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
          <h3>{title}</h3>
          {body ? <p>{body}</p> : null}
        </div>
        <StatusBadge tone={statusTone[status]}>{metadata ?? status}</StatusBadge>
      </div>
      {children ? <div className="module-panel__body">{children}</div> : null}
    </article>
  );
}
