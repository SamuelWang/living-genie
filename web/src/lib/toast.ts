import { Toast } from '@base-ui/react/toast';

export const toastManager = Toast.createToastManager();

const DEFAULT_DURATIONS = {
  success: 3000,
  error: 5000,
} as const;

export const toast = {
  success: (description: string) =>
    toastManager.add({ type: 'success', description, timeout: DEFAULT_DURATIONS.success }),
  error: (description: string) =>
    toastManager.add({ type: 'error', description, timeout: DEFAULT_DURATIONS.error }),
};
