import { useState, type SubmitEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate, useSearchParams } from 'react-router';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { resendVerification, verifyEmail } from '@/api/auth';
import { toast } from '@/lib/toast';

export function VerifyEmailPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams] = useSearchParams();

  const emailFromParams = Boolean(searchParams.get('email'));
  const [email, setEmail] = useState(searchParams.get('email') ?? '');
  const [code, setCode] = useState('');
  const [touched, setTouched] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const verifyMutation = useMutation({ mutationFn: verifyEmail });
  const resendMutation = useMutation({ mutationFn: resendVerification });

  const emailValid = email.trim().length > 0;
  const codeValid = code.trim().length > 0;

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    setTouched(true);
    setFormError(null);
    if (!emailValid || !codeValid) return;

    verifyMutation.mutate(
      { email, code },
      {
        onSuccess: (user) => {
          queryClient.setQueryData(['auth', 'me'], user);
          toast.success(t('auth.verifyEmailSuccess'));
          void navigate('/diaries', { replace: true });
        },
        onError: () => {
          const message = t('auth.invalidOrExpiredCode');
          setFormError(message);
          toast.error(message);
        },
      },
    );
  };

  const handleResend = () => {
    if (!emailValid) {
      setTouched(true);
      return;
    }
    resendMutation.mutate(
      { email },
      { onSuccess: () => toast.success(t('auth.verifyEmailResendSuccess')) },
    );
  };

  return (
    <div className='mx-auto flex max-w-sm flex-col gap-4'>
      <h1 className='text-2xl font-semibold'>{t('auth.verifyEmailTitle')}</h1>
      <form className='flex flex-col gap-4' noValidate onSubmit={handleSubmit}>
        <div className='flex flex-col gap-1.5'>
          <Label htmlFor='verify-email-email'>{t('auth.emailLabel')}</Label>
          <Input
            id='verify-email-email'
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
          <Label htmlFor='verify-email-code'>{t('auth.verifyEmailCodeLabel')}</Label>
          <Input
            id='verify-email-code'
            type='text'
            value={code}
            onChange={(e) => setCode(e.target.value)}
            aria-invalid={touched && !codeValid}
          />
          {touched && !codeValid && (
            <p role='alert' className='text-destructive text-xs'>
              {t('auth.verifyEmailCodeRequired')}
            </p>
          )}
        </div>

        {formError && (
          <p role='alert' className='text-destructive text-sm'>
            {formError}
          </p>
        )}

        <Button type='submit' disabled={verifyMutation.isPending}>
          {t('auth.verifyEmailSubmit')}
        </Button>
      </form>
      <p className='text-muted-foreground text-sm'>
        {t('auth.verifyEmailResendPrompt')}{' '}
        <button
          type='button'
          className='text-primary underline underline-offset-4'
          onClick={handleResend}
          disabled={resendMutation.isPending}
        >
          {t('auth.verifyEmailResendAction')}
        </button>
      </p>
    </div>
  );
}
