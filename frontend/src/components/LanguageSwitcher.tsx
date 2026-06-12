import { useI18n, type Language } from '../i18n';

const options: Array<{ value: Language; label: string }> = [
  { value: 'es', label: 'ES' },
  { value: 'en', label: 'EN' },
];

export function LanguageSwitcher() {
  const { language, setLanguage, t } = useI18n();

  return (
    <div className="language-switcher" aria-label={t('language.label')}>
      {options.map((option) => (
        <button
          aria-pressed={language === option.value}
          className="language-switcher__option"
          key={option.value}
          onClick={() => setLanguage(option.value)}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}
