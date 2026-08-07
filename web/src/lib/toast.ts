import { Toast } from '@base-ui/react/toast';

export const toastManager = Toast.createToastManager();

export const toast = {
  success: (description: string) => toastManager.add({ type: 'success', description }),
  error: (description: string) => toastManager.add({ type: 'error', description }),
};
