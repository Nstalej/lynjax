import { Panel, StatusCards, type StatusCard } from '../components/DashboardCards';
import { assessmentSummary, brandTokens, formatUpdatedAt } from '../lib/brand';

const statusCards: StatusCard[] = [
  {
    label: 'Activos Visibles',
    value: '23',
    detail: 'Inventario normalizado desde el último barrido seguro.',
    tone: 'stable',
  },
  {
    label: 'Hallazgos Priorizados',
    value: '7',
    detail: 'Servicios expuestos requieren validación manual.',
    tone: 'watch',
  },
  {
    label: 'Evidencias Vinculadas',
    value: '12',
    detail: 'Capturas, checks y trazas listas para reporte.',
    tone: 'stable',
  },
  {
    label: 'Riesgo Crítico',
    value: '1',
    detail: 'Revisar acceso administrativo sin segmentación.',
    tone: 'alert',
  },
];

export function LynjaxDashboard() {
  return (
    <>
      <a className="skip-link" href="#main-content">
        Saltar al Contenido
      </a>
      <div className="app-shell">
        <header className="site-header" aria-label="Navegación Principal">
          <a className="brand-mark" href="#top" translate="no" aria-label="Lynjax Inicio">
            <span className="brand-mark__glyph" aria-hidden="true">Lx</span>
            <span>Lynjax</span>
          </a>
          <nav aria-label="Secciones de Demo">
            <a href="#assessment">Assessment</a>
            <a href="#evidence">Evidencia</a>
            <a href="#report">Reporte</a>
          </nav>
        </header>

        <main id="main-content">
          <section className="hero" id="top" aria-labelledby="hero-title">
            <div className="hero__copy">
              <p className="eyebrow">Intelligent Network Visibility</p>
              <h1 id="hero-title">Lynjax Convierte Assessments de Red en Evidencia Accionable</h1>
              <p className="hero__lead">
                Una base visual para descubrir activos, priorizar hallazgos y entregar reportes claros sin perder trazabilidad técnica.
              </p>
              <div className="hero__actions" aria-label="Acciones Principales">
                <a className="button button--primary" href="#assessment">Ver Dashboard Demo</a>
                <a className="button button--secondary" href="#report">Explorar Reporte</a>
              </div>
            </div>
            <aside className="hero-card" aria-label="Resumen Lynjax">
              <p className="hero-card__label" translate="no">{brandTokens.tagline}</p>
              <div className="network-orbit" aria-hidden="true">
                <span />
                <span />
                <span />
              </div>
              <dl>
                <div>
                  <dt>Target</dt>
                  <dd>{assessmentSummary.target}</dd>
                </div>
                <div>
                  <dt>Última Actualización</dt>
                  <dd>{formatUpdatedAt(assessmentSummary.updatedAt)}</dd>
                </div>
              </dl>
            </aside>
          </section>

          <StatusCards cards={statusCards} />

          <div className="dashboard-grid">
            <Panel title="Assessment Panel" eyebrow="Flujo Controlado">
              <div className="assessment-list" id="assessment">
                {assessmentSummary.checks.map((check) => (
                  <article className="assessment-item" key={check.name}>
                    <div className="assessment-item__meta">
                      <h3>{check.name}</h3>
                      <p>{check.result}</p>
                    </div>
                    <span>{check.state}</span>
                  </article>
                ))}
              </div>
            </Panel>

            <Panel title="Mapa de Evidencia" eyebrow="Trazabilidad Técnica">
              <div className="evidence-map" id="evidence" aria-label="Mapa de Evidencia de Red">
                <div className="node node--core">Core</div>
                <div className="node node--asset">Gateway</div>
                <div className="node node--asset">Switch Lab</div>
                <div className="node node--finding">Finding 01</div>
              </div>
            </Panel>
          </div>

          <section className="report-placeholder" id="report" aria-labelledby="report-title">
            <div>
              <p className="eyebrow">Reporte Ejecutivo</p>
              <h2 id="report-title">Placeholder de Reporte Lynjax</h2>
              <p>
                Próximo entregable: resumen de alcance, evidencia vinculada, hallazgos priorizados y recomendaciones listas para revisión.
              </p>
            </div>
            <a className="button button--secondary" href="#top">Volver Arriba</a>
          </section>
        </main>
      </div>
    </>
  );
}
