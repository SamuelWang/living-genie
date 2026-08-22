import { useState, type SubmitEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { resetPassword } from '@/api/auth';
import { PASSWORD_MIN_LENGTH } from '@/lib/auth';
import { toast } from '@/lib/toast';

export function ResetPasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const emailFromParams = Boolean(searchParams.get('email'));
  const [email, setEmail] = useState(searchParams.get('email') ?? '');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [touched, setTouched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const resetMutation = useMutation({ mutationFn: resetPassword });

  const emailValid = email.trim().length > 0;
  const codeValid = code.trim().length > 0;
  const passwordValid = newPassword.length >= PASSWORD_MIN_LENGTH;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    setFormError(null);
    if (!emailValid || !codeValid || !passwordValid) return;

    resetMutation.mutate(
      { email, code, new_password: newPassword },
      {
        onSuccess: () => {
          toast.success(t('auth.resetPasswordSuccess'));
          void navigate('/login', { replace: true });
        },
        onError: () => {
          const message = t('auth.invalidOrExpiredCode');
          setFormError(message);
          toast.error(message);
        },
      },
    );
  };

  return (
    <div className='mx-auto flex max-w-sm flex-col gap-4'>
      <h1 className='text-2xl font-semibold'>{t('auth.resetPasswordTitle')}</h1>
      <form className='flex flex-col gap-4' noValidate onSubmit={handleSubmit}>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='reset-password-email'>{t('auth.emailLabel')}</Label>
          <Input
            id='reset-password-email'
            type='email'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={touched && !emailValid}
            readOnly={emailFromParams}
            className={emailFromParams ? 'bg-muted/50' : undefined}
          />
          {touched && !emailValid && (
            <p role='alert' className='text-destructive text-xs'>
              {t('auth.emailRequired')}
            </p>
          )}
        </div>

        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='reset-password-code'>{t('auth.resetPasswordCodeLabel')}</Label>
          <Input
            id='reset-password-code'
            type='text'
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-invalid={touched && !codeValid}
          />
          {touched && !codeValid && (
            <p role='alert' className='text-destructive text-xs'>
              {t('auth.resetPasswordCodeRequired')}
            </p>
          )}
        </div>

        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='reset-password-new-password'>{t('auth.resetPasswordNewPasswordLabel')}</Label>
          <Input
            id='reset-password-new-password'
            type='password'
            value={newPassword}
            maxLength={72}
            onChange={(e) => setNewPassword(e.target.value)}
            aria-invalid={touched && !passwordValid}
          />
          {touched && !passwordValid && (
            <p role='alert' className='text-destructive text-xs'>
              {newPassword.length === 0
                ? t('auth.passwordRequired')
                : t('auth.passwordTooShort', { min: PASSWORD_MIN_LENGTH })}
            </p>
          )}
        </div>

        {formError && (
          <p role='alert' className='text-destructive text-sm'>
            {formError}
          </p>
        )}

        <Button type='submit' disabled={resetMutation.isPending}>
          {t('auth.resetPasswordSubmit')}
        </Button>
      </form>
    </div>
  );
}
