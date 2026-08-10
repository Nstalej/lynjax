import { useState, type ReactNode } from 'react';
import { navItems } from '../components/nav/navItems';
import type { Account } from '../lib/api';
import { AgentsPage } from '../pages/AgentsPage';
import { AuditsPage } from '../pages/AuditsPage';
import { DashboardPage } from '../pages/DashboardPage';
import { DevicesPage } from '../pages/DevicesPage';
import { SettingsPage } from '../pages/SettingsPage';

/** The console: a sidebar, a header strip, and the active module. */
export function AppShell({
  account,
  onSignOut,
}: {
  account: Account;
  onSignOut: () => void;
}) {
  const [active, setActive] = useState<string>('dashboard');
  const [collapsed, setCollapsed] = useState(false);

  const pages: Record<string, ReactNode> = {
    dashboard: <DashboardPage onNavigate={setActive} />,
    devices: <DevicesPage />,
    agents: <AgentsPage />,
    audits: <AuditsPage />,
    settings: <SettingsPage account={account} />,
  };

  const current = navItems.find((item) => item.id === active) ?? navItems[0];

  return (
    <div className={`console ${collapsed ? 'console--collapsed' : ''}`}>
      <aside className="console__nav">
        <div className="console__brand">
          <span className="console__mark" aria-hidden="true" />
          <strong className="console__name">Lynjax</strong>
        </div>

        <nav>
          {navItems.map((item) => (
            <button
              className={`nav-item ${item.id === active ? 'nav-item--active' : ''}`}
              key={item.id}
              onClick={() => setActive(item.id)}
              title={item.label}
              type="button"
            >
              <span aria-hidden="true">{item.icon}</span>
              <span className="nav-item__label">{item.label}</span>
            </button>
          ))}
        </nav>

        <button
          className="console__collapse"
          onClick={() => setCollapsed((value) => !value)}
          title={collapsed ? 'Expandir' : 'Contraer'}
          type="button"
        >
          {collapsed ? '»' : '«'}
        </button>
      </aside>

      <div className="console__body">
        <header className="console__header">
          <h1>{current.label}</h1>
          <div className="console__session">
            <span title={`Rol: ${account.role}`}>
              {account.email} · {account.role}
            </span>
            <button className="button button--ghost" onClick={onSignOut} type="button">
              Salir
            </button>
          </div>
        </header>

        <main className="console__main">{pages[active]}</main>
      </div>
    </div>
  );
}
