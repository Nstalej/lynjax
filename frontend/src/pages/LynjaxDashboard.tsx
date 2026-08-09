import { useState } from 'react';
import type { NavItem } from '../components/nav/navItems';
import { EmptyState } from '../components/ui/EmptyState';
import { ModulePanel } from '../components/ui/ModulePanel';
import { StatusBadge } from '../components/ui/StatusBadge';
import { StatusCard } from '../components/ui/StatusCard';
import { useI18n } from '../i18n';
import { assets, evidenceRecords, moduleInsights, platformMetrics } from '../lib/mockData';

export function OverviewPage({ onNavigate }: { onNavigate: (moduleId: string) => void }) {
  const { t } = useI18n();

  return (
    <div className="module-stack">
      <section className="hero-panel" aria-labelledby="overview-title">
        <div>
          <p className="eyebrow">{t('app.tagline')}</p>
          <h2 id="overview-title">{t('overview.heroTitle')}</h2>
          <p>{t('overview.heroBody')}</p>
          <div className="hero-panel__actions">
            <button className="button button--primary" onClick={() => onNavigate('connectivity')} type="button">
              Ejecutar demo segura
            </button>
            <button className="button button--secondary" onClick={() => onNavigate('evidence')} type="button">
              {t('overview.secondaryAction')}
            </button>
          </div>
        </div>
        <div className="network-orbit" aria-hidden="true">
          <span />
          <span />
          <span />
        </div>
      </section>

      <section className="status-grid" aria-label={t('topbar.status')}>
        {platformMetrics.map((metric) => (
          <StatusCard key={metric.id} {...metric} />
        ))}
      </section>

      <section className="module-panel-grid" aria-label="Módulos v1.0">
        <ModulePanel
          title="Assessment → evidence → report"
          eyebrow="v1.0 flow"
          body="Un endpoint local devuelve resultados estructurados, evidencia simulada y Markdown renderizado desde la misma respuesta."
          status="ready"
          metadata="wired"
        />
        <ModulePanel
          title="Sandbox primero"
          eyebrow="Safety"
          body="Solo targets sanitizados: target-web y target-metadata. No credenciales, sockets externos o instalaciones del host."
          status="readonly"
          metadata="safe"
        />
        <ModulePanel
          title="Día 4 preparado"
          eyebrow="Virtual lab"
          body="La ruta siguiente formaliza Docker/Containerlab en WSL2/VM/CI sin tocar Windows directamente."
          status="planned"
          metadata="next"
        />
      </section>
    </div>
  );
}

export function ModulePage({ item }: { item: NavItem }) {
  const { t } = useI18n();
  const isReadonly = item.status === 'readonly';

  return (
    <section className="module-page" aria-labelledby={`${item.id}-title`}>
      <div className="module-page__header">
        <div>
          <p className="eyebrow">{t('modulePage.kicker')}</p>
          <h2 id={`${item.id}-title`}>{t(item.labelKey)}</h2>
          <p>{t(item.descriptionKey)}</p>
        </div>
        <StatusBadge tone={isReadonly ? 'neutral' : item.status === 'planned' ? 'watch' : 'stable'}>
          {item.badgeKey ? t(item.badgeKey) : item.status === 'ready' ? t('badge.ready') : t('badge.planned')}
        </StatusBadge>
      </div>

      {isReadonly ? <p className="readonly-notice">{t('page.readonlyNotice')}</p> : null}

      {renderModuleContent(item)}
    </section>
  );
}

function renderModuleContent(item: NavItem) {
  switch (item.id) {
    case 'evidence':
      return <EvidencePage />;
    case 'topology':
      return <TopologyPage />;
    case 'directory':
    case 'intelligence':
      return <InsightPanels moduleId={item.id} emptyTitle="Módulo planificado" />;
    default:
      return <InsightPanels moduleId={item.id} emptyTitle="Área preparada" />;
  }
}

function AssetsPage() {
  return (
    <div className="data-list">
      {assets.map((asset) => (
        <ModulePanel key={asset.id} title={asset.name} eyebrow={asset.kind} status={asset.status === 'observed' ? 'ready' : asset.status === 'planned' ? 'planned' : 'active'} metadata={asset.status}>
          <dl className="compact-dl">
            <div><dt>Zona</dt><dd>{asset.zone}</dd></div>
            <div><dt>Origen</dt><dd>Inventario sanitizado</dd></div>
          </dl>
        </ModulePanel>
      ))}
    </div>
  );
}

function EvidencePage() {
  return (
    <div className="data-list">
      {evidenceRecords.map((record) => (
        <ModulePanel key={record.id} title={record.title} eyebrow={record.source} status={record.status === 'pending' ? 'planned' : 'ready'} metadata={record.status}>
          <dl className="compact-dl">
            <div><dt>Retención</dt><dd>{record.retention}</dd></div>
            <div><dt>Seguridad</dt><dd>Sin credenciales ni datos reales</dd></div>
          </dl>
        </ModulePanel>
      ))}
    </div>
  );
}

function ReportsPage() {
  return (
    <div className="module-stack">
      <InsightPanels moduleId="reports" emptyTitle="Reportes preparados" />
      <div className="report-preview">
        <p className="eyebrow">Preview</p>
        <h3>Markdown generado por backend</h3>
        <p>El módulo de conectividad muestra el reporte real cuando el endpoint local responde. Esta página reserva el espacio para historial/export.</p>
      </div>
    </div>
  );
}

function TopologyPage() {
  return (
    <div className="module-stack">
      <div className="topology-map" aria-label="Topología sanitizada">
        <span className="topology-node topology-node--core">Lynjax Core</span>
        <span className="topology-node topology-node--edge">Lab Edge</span>
        <span className="topology-node topology-node--web">target-web</span>
        <span className="topology-node topology-node--metadata">target-metadata</span>
      </div>
      <InsightPanels moduleId="topology" emptyTitle="Topología planificada" />
    </div>
  );
}

function InsightPanels({ moduleId, emptyTitle }: { moduleId: string; emptyTitle: string }) {
  const insights = moduleInsights[moduleId] ?? [];

  if (insights.length === 0) {
    return <EmptyState title={emptyTitle} body="Placeholder visual reservado para la versión candidata; la integración real queda fuera de este alcance seguro." />;
  }

  return (
    <div className="module-panel-grid">
      {insights.map((insight) => (
        <ModulePanel key={insight.id} title={insight.title} body={insight.body} status={insight.status} metadata={insight.metadata} />
      ))}
    </div>
  );
}

