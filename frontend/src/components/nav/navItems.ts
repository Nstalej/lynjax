/**
 * The menu.
 *
 * Five entries, the ones NetVault had. The previous list was ten modules with
 * descriptions and "planned" badges, which is a product tour rather than a
 * console. Topology became a Dashboard panel and Reports an action inside
 * Audits, because neither is somewhere an operator navigates to on its own.
 */
export type NavItem = {
  id: 'dashboard' | 'devices' | 'agents' | 'audits' | 'settings';
  label: string;
  icon: string;
};

export const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '◧' },
  { id: 'devices', label: 'Dispositivos', icon: '▦' },
  { id: 'agents', label: 'Agentes', icon: '◉' },
  { id: 'audits', label: 'Auditorías', icon: '✓' },
  { id: 'settings', label: 'Configuración', icon: '⚙' },
];
