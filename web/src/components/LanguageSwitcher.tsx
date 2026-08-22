import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { updateLocale } from '@/api/auth';
import { useAuth } from '@/hooks/useAuth';

const LOCALES = [
  { code: 'zh-Hant', label: '中文' },
  { code: 'en', label: 'EN' },
] as const;

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const { user } = useAuth();
  const updateLocaleMutation = useMutation({ mutationFn: updateLocale });

  const handleChange = (code: (typeof LOCALES)[number]['code']) => {
    void i18n.changeLanguage(code);
    if (user) {
      updateLocaleMutation.mutate({ locale: code });
    }
  };

  return (
    <div className="flex gap-1">
      {LOCALES.map(({ code, label }) => (
        <Button
          key={code}
          variant={i18n.resolvedLanguage === code ? 'default' : 'outline'}
          size="sm"
          onClick={() => handleChange(code)}
        >
          {label}
        </Button>
      ))}
    </div>
  );
}
