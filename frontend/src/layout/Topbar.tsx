import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { useI18n } from '../i18n';

export function Topbar({ onOpenMobile }: { onOpenMobile: () => void }) {
  const { t } = useI18n();

  return (
    <header className="topbar">
      <button className="topbar__menu" onClick={onOpenMobile} type="button">
        <span aria-hidden="true">☰</span>
        <span className="sr-only">{t('sidebar.openMobile')}</span>
      </button>
      <div className="topbar__copy">
        <p className="eyebrow">{t('topbar.eyebrow')}</p>
        <h1>{t('topbar.title')}</h1>
        <p>{t('topbar.subtitle')}</p>
      </div>
      <div className="topbar__actions">
        <span className="topbar__status">{t('topbar.status')}</span>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
