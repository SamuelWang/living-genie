import { useState, type SubmitEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useAuth } from '@/hooks/useAuth';
import { ApiError } from '@/api/errors';

export function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [touched, setTouched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loginMutation = useMutation({ mutationFn: login });

  const emailValid = email.trim().length > 0;
  const passwordValid = password.length > 0;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    setFormError(null);
    if (!emailValid || !passwordValid) return;

    loginMutation.mutate(
      { email, password },
      {
        onSuccess: () => navigate('/diaries', { replace: true }),
        onError: (err) => {
          if (err instanceof ApiError && err.status === 401) {
            setFormError(t('auth.invalidCredentials'));
          } else {
            setFormError(t('common.genericError'));
          }
        },
      },
    );
  };

  return (
    <div className='mx-auto flex max-w-sm flex-col gap-4'>
      <h1 className='text-2xl font-semibold'>{t('auth.loginTitle')}</h1>
      <form className='flex flex-col gap-4' noValidate onSubmit={handleSubmit}>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='login-email'>{t('auth.emailLabel')}</Label>
          <Input
            id='login-email'
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

        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='login-password'>{t('auth.passwordLabel')}</Label>
          <Input
            id='login-password'
            type='password'
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={touched && !passwordValid}
          />
          {touched && !passwordValid && (
            <p role='alert' className='text-destructive text-xs'>
              {t('auth.passwordRequired')}
            </p>
          )}
        </div>

        {formError && (
          <p role='alert' className='text-destructive text-sm'>
            {formError}
          </p>
        )}

        <Button type='submit' disabled={loginMutation.isPending}>
          {t('auth.loginSubmit')}
        </Button>
      </form>
      <p className='text-muted-foreground text-sm'>
        {t('auth.registerNoAccount')}{' '}
        <Link to='/register' className='text-primary underline underline-offset-4'>
          {t('auth.registerLink')}
        </Link>
      </p>
    </div>
  );
}
