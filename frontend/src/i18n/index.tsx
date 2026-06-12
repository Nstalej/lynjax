import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import en from './locales/en/common.json';
import es from './locales/es/common.json';

export type Language = 'es' | 'en';

type Dictionary = typeof es;
type TranslationKey = keyof Dictionary;

type I18nContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (key: TranslationKey) => string;
};

const dictionaries: Record<Language, Dictionary> = { es, en };
const storageKey = 'lynjax.language';

function getInitialLanguage(): Language {
  if (typeof window === 'undefined') {
    return 'es';
  }

  const stored = window.localStorage.getItem(storageKey);
  if (stored === 'en' || stored === 'es') {
    return stored;
  }

  return window.navigator.language.toLowerCase().startsWith('en') ? 'en' : 'es';
}

const I18nContext = createContext<I18nContextValue | undefined>(undefined);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(getInitialLanguage);

  const setLanguage = useCallback((nextLanguage: Language) => {
    setLanguageState(nextLanguage);
    window.localStorage.setItem(storageKey, nextLanguage);
    document.documentElement.lang = nextLanguage;
  }, []);

  const value = useMemo<I18nContextValue>(() => ({
    language,
    setLanguage,
    t: (key) => dictionaries[language][key] ?? key,
  }), [language, setLanguage]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error('useI18n must be used inside I18nProvider');
  }

  return context;
}

export type { TranslationKey };
