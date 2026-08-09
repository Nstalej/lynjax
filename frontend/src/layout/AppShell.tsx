import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { navItems } from '../components/nav/navItems';
import { useI18n } from '../i18n';
import { AssetsPage } from '../pages/AssetsPage';
import { AuditPage } from '../pages/AuditPage';
import { DiscoveryPage } from '../pages/DiscoveryPage';
import { ModulePage, OverviewPage } from '../pages/LynjaxDashboard';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';

export function AppShell() {
  const { language, t } = useI18n();
  const [activeModule, setActiveModule] = useState('overview');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const activeItem = useMemo(
    () => navItems.find((item) => item.id === activeModule) ?? navItems[0],
    [activeModule],
  );

  // Modules backed by the real API render their own page; the rest still show
  // the placeholder panel, which is honest about what is not built yet.
  let content: ReactNode;
  if (activeItem.id === 'overview') {
    content = <OverviewPage onNavigate={setActiveModule} />;
  } else if (activeItem.id === 'assets') {
    content = <AssetsPage />;
  } else if (activeItem.id === 'assessments' || activeItem.id === 'reports') {
    content = <AuditPage />;
  } else if (activeItem.id === 'connectivity') {
    content = <DiscoveryPage />;
  } else {
    content = <ModulePage item={activeItem} />;
  }

  return (
    <>
      <a className="skip-link" href="#main-content">{t('app.skipLink')}</a>
      <div className={`platform-shell ${sidebarCollapsed ? 'platform-shell--collapsed' : ''}`}>
        <Sidebar
          activeModule={activeItem.id}
          collapsed={sidebarCollapsed}
          mobileOpen={mobileOpen}
          onCloseMobile={() => setMobileOpen(false)}
          onNavigate={setActiveModule}
          onToggleCollapsed={() => setSidebarCollapsed((current) => !current)}
        />
        <div className="platform-shell__workspace">
          <Topbar onOpenMobile={() => setMobileOpen(true)} />
          <main className="platform-main" id="main-content" tabIndex={-1}>
            {content}
          </main>
          <footer className="platform-footer">{t('footer.safety')}</footer>
        </div>
      </div>
    </>
  );
}
