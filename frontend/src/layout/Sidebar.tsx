import { navItems } from '../components/nav/navItems';
import { useI18n } from '../i18n';

type SidebarProps = {
  activeModule: string;
  collapsed: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
  onNavigate: (moduleId: string) => void;
  onToggleCollapsed: () => void;
};

export function Sidebar({
  activeModule,
  collapsed,
  mobileOpen,
  onCloseMobile,
  onNavigate,
  onToggleCollapsed,
}: SidebarProps) {
  const { t } = useI18n();

  return (
    <>
      <aside className={`sidebar ${collapsed ? 'sidebar--collapsed' : ''} ${mobileOpen ? 'sidebar--mobile-open' : ''}`}>
        <div className="sidebar__brand">
          <span className="brand-mark__glyph" aria-hidden="true">Lx</span>
          <div className="sidebar__brand-copy">
            <strong translate="no">{t('app.product')}</strong>
            <span>{t('app.tagline')}</span>
          </div>
        </div>

        <nav aria-label={t('sidebar.label')} className="sidebar__nav">
          {navItems.map((item) => (
            <button
              aria-current={activeModule === item.id ? 'page' : undefined}
              className="sidebar__nav-item"
              key={item.id}
              onClick={() => {
                onNavigate(item.id);
                onCloseMobile();
              }}
              type="button"
            >
              <span className="sidebar__nav-dot" aria-hidden="true" />
              <span className="sidebar__nav-copy">
                <strong>{t(item.labelKey)}</strong>
                <small>{t(item.descriptionKey)}</small>
              </span>
              {item.badgeKey ? <span className="sidebar__badge">{t(item.badgeKey)}</span> : null}
            </button>
          ))}
        </nav>

        <button
          aria-label={collapsed ? t('sidebar.expand') : t('sidebar.collapse')}
          className="sidebar__collapse"
          onClick={onToggleCollapsed}
          type="button"
        >
          <span aria-hidden="true">{collapsed ? '›' : '‹'}</span>
          <span>{collapsed ? t('sidebar.expand') : t('sidebar.collapse')}</span>
        </button>
      </aside>
      <button
        aria-label={t('sidebar.closeMobile')}
        className={`mobile-scrim ${mobileOpen ? 'mobile-scrim--visible' : ''}`}
        onClick={onCloseMobile}
        type="button"
      />
    </>
  );
}
