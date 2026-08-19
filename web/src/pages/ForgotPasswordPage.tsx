import { useState, type SubmitEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { forgotPassword } from '@/api/auth';

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [email, setEmail] = useState('');
  const [touched, setTouched] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const forgotMutation = useMutation({ mutationFn: forgotPassword });

  const emailValid = email.trim().length > 0;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    if (!emailValid) return;

    forgotMutation.mutate({ email }, { onSettled: () => setSubmitted(true) });
  };

  if (submitted) {
    return (
      <div className='mx-auto flex max-w-sm flex-col gap-4'>
        <h1 className='text-2xl font-semibold'>{t('auth.forgotPasswordTitle')}</h1>
        <p className='text-sm'>{t('auth.forgotPasswordSuccess')}</p>
        <p className='text-muted-foreground text-sm'>
          <Link
            to={`/reset-password?email=${encodeURIComponent(email)}`}
            className='text-primary underline underline-offset-4'
          >
            {t('auth.forgotPasswordResetLink')}
          </Link>
        </p>
      </div>
    );
  }

  return (
    <div className='mx-auto flex max-w-sm flex-col gap-4'>
      <h1 className='text-2xl font-semibold'>{t('auth.forgotPasswordTitle')}</h1>
      <form className='flex flex-col gap-4' noValidate onSubmit={handleSubmit}>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='forgot-password-email'>{t('auth.emailLabel')}</Label>
          <Input
            id='forgot-password-email'
            type='email'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={touched && !emailValid}
          />
          {touched && !emailValid && (
            <p role='alert' className='text-destructive text-xs'>
              {t('auth.emailRequired')}
            </p>
          )}
        </div>

        <Button type='submit' disabled={forgotMutation.isPending}>
          {t('auth.forgotPasswordSubmit')}
        </Button>
      </form>
    </div>
  );
}
