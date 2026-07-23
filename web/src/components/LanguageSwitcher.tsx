import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';

const LOCALES = [
  { code: 'zh-Hant', label: '中文' },
  { code: 'en', label: 'EN' },
] as const;

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  return (
    <div className="flex gap-1">
      {LOCALES.map(({ code, label }) => (
        <Button
          key={code}
          variant={i18n.resolvedLanguage === code ? 'default' : 'outline'}
          size="sm"
          onClick={() => i18n.changeLanguage(code)}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}
