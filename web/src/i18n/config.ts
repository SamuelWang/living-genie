import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import en from '../locales/en/translation.json';
import zhHant from '../locales/zh-Hant/translation.json';

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      'zh-Hant': { translation: zhHant },
    },
    fallbackLng: 'zh-Hant',
    supportedLngs: ['zh-Hant', 'en'],
    interpolation: { escapeValue: false },
    detection: {
      order: ['localStorage', 'navigator'],
      lookupLocalStorage: 'living-genie-language',
      caches: ['localStorage'],
    },
  });

export default i18n;
