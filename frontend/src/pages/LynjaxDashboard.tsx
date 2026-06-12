import type { NavItem } from '../components/nav/navItems';
import { useI18n, type TranslationKey } from '../i18n';

type Metric = {
  labelKey: TranslationKey;
  detailKey: TranslationKey;
  value: string;
  tone: 'stable' | 'watch' | 'alert';
  statusKey: TranslationKey;
};

const metrics: Metric[] = [
  { labelKey: 'metric.assets', detailKey: 'metric.assetsDetail', value: '23', tone: 'stable', statusKey: 'status.operational' },
  { labelKey: 'metric.findings', detailKey: 'metric.findingsDetail', value: '7', tone: 'watch', statusKey: 'status.watch' },
  { labelKey: 'metric.evidence', detailKey: 'metric.evidenceDetail', value: '12', tone: 'stable', statusKey: 'status.operational' },
  { labelKey: 'metric.risk', detailKey: 'metric.riskDetail', value: '1', tone: 'alert', statusKey: 'status.priority' },
];

const workflowCards: Array<{ titleKey: TranslationKey; bodyKey: TranslationKey }> = [
  { titleKey: 'workflow.safeScope', bodyKey: 'workflow.safeScopeBody' },
  { titleKey: 'workflow.backendNext', bodyKey: 'workflow.backendNextBody' },
  { titleKey: 'workflow.labReady', bodyKey: 'workflow.labReadyBody' },
];

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
            <button className="button button--primary" onClick={() => onNavigate('assessments')} type="button">
              {t('overview.primaryAction')}
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
        {metrics.map((metric) => (
          <article className={`status-card status-card--${metric.tone}`} key={metric.labelKey}>
            <div className="status-card__header">
              <p>{t(metric.labelKey)}</p>
              <span>{t(metric.statusKey)}</span>
            </div>
            <strong>{metric.value}</strong>
            <small>{t(metric.detailKey)}</small>
          </article>
        ))}
      </section>

      <section className="panel" aria-labelledby="workflow-title">
        <p className="eyebrow">{t('section.workflow')}</p>
        <h2 id="workflow-title">{t('section.workflowTitle')}</h2>
        <div className="module-card-grid">
          {workflowCards.map((card) => (
            <article className="module-card" key={card.titleKey}>
              <h3>{t(card.titleKey)}</h3>
              <p>{t(card.bodyKey)}</p>
            </article>
          ))}
        </div>
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
        <span className={`module-badge module-badge--${item.status}`}>
          {item.badgeKey ? t(item.badgeKey) : item.status === 'ready' ? t('badge.ready') : t('badge.planned')}
        </span>
      </div>

      {isReadonly ? <p className="readonly-notice">{t('page.readonlyNotice')}</p> : null}

      <div className="module-card-grid">
        {getModuleCards(item.id).map((key) => (
          <article className="module-card" key={key}>
            <p>{t(key)}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function getModuleCards(moduleId: string): TranslationKey[] {
  if (moduleId === 'directory') {
    return ['directory.card1', 'directory.card2'];
  }

  if (moduleId === 'intelligence') {
    return ['intelligence.card1', 'intelligence.card2'];
  }

  if (moduleId === 'settings') {
    return ['settings.card1', 'settings.card2'];
  }

  return ['page.defaultCta'];
}
