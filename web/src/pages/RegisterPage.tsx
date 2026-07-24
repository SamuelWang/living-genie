import { useState, type SubmitEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { register } from '@/api/auth';
import { ApiError } from '@/api/errors';

const PASSWORD_MIN_LENGTH = 8;

export function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [touched, setTouched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const registerMutation = useMutation({ mutationFn: register });

  const emailValid = email.trim().length > 0 && /\S+@\S+\.\S+/.test(email);
  const passwordValid = password.length >= PASSWORD_MIN_LENGTH;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    setFormError(null);
    if (!emailValid || !passwordValid) return;

    registerMutation.mutate(
      { email, password },
      {
        onSuccess: () => navigate('/login', { replace: true }),
        onError: (err) => {
          if (err instanceof ApiError && err.status === 409) {
            setFormError(t('auth.registerDuplicateEmail'));
          } else {
            setFormError(t('common.genericError'));
          }
        },
      },
    );
  };

  return (
    <div className='mx-auto flex max-w-sm flex-col gap-4'>
      <h1 className='text-2xl font-semibold'>{t('auth.registerTitle')}</h1>
      <form className='flex flex-col gap-4' noValidate onSubmit={handleSubmit}>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='register-email'>{t('auth.emailLabel')}</Label>
          <Input
            id='register-email'
            type='email'
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-invalid={touched && !emailValid}
          />
          {touched && !emailValid && (
            <p role='alert' className='text-destructive text-xs'>
              {email.trim().length === 0 ? t('auth.emailRequired') : t('auth.emailInvalid')}
            </p>
          )}
        </div>

        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='register-password'>{t('auth.passwordLabel')}</Label>
          <Input
            id='register-password'
            type='password'
            value={password}
            maxLength={72}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={touched && !passwordValid}
          />
          {touched && !passwordValid && (
            <p role='alert' className='text-destructive text-xs'>
              {password.length === 0
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

        <Button type='submit' disabled={registerMutation.isPending}>
          {t('auth.registerSubmit')}
        </Button>
      </form>
      <p className='text-muted-foreground text-sm'>
        {t('auth.registerHaveAccount')}{' '}
        <Link to='/login' className='text-primary underline underline-offset-4'>
          {t('auth.registerLoginLink')}
        </Link>
      </p>
    </div>
  );
}
