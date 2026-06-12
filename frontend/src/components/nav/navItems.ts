import type { TranslationKey } from '../../i18n';

export type NavItem = {
  id: string;
  labelKey: TranslationKey;
  descriptionKey: TranslationKey;
  badgeKey?: TranslationKey;
  status: 'active' | 'ready' | 'planned' | 'readonly';
};

export const navItems: NavItem[] = [
  { id: 'overview', labelKey: 'nav.overview', descriptionKey: 'module.overview.summary', status: 'active' },
  { id: 'assets', labelKey: 'nav.assets', descriptionKey: 'module.assets.summary', status: 'ready' },
  { id: 'connectivity', labelKey: 'nav.connectivity', descriptionKey: 'module.connectivity.summary', status: 'ready' },
  { id: 'assessments', labelKey: 'nav.assessments', descriptionKey: 'module.assessments.summary', status: 'ready' },
  { id: 'evidence', labelKey: 'nav.evidence', descriptionKey: 'module.evidence.summary', status: 'ready' },
  { id: 'reports', labelKey: 'nav.reports', descriptionKey: 'module.reports.summary', status: 'ready' },
  { id: 'topology', labelKey: 'nav.topology', descriptionKey: 'module.topology.summary', status: 'planned' },
  { id: 'directory', labelKey: 'nav.directory', descriptionKey: 'module.directory.summary', badgeKey: 'badge.readonlyPlanned', status: 'readonly' },
  { id: 'intelligence', labelKey: 'nav.intelligence', descriptionKey: 'module.intelligence.summary', badgeKey: 'badge.readonlyPlanned', status: 'readonly' },
  { id: 'settings', labelKey: 'nav.settings', descriptionKey: 'module.settings.summary', status: 'planned' },
];
