import type { ApiErrorDetail } from './types';

export class ApiError extends Error {
  readonly status: number;
  readonly detail: ApiErrorDetail;

  constructor(status: number, detail: ApiErrorDetail) {
    super(typeof detail === 'string' ? detail : 'Validation error');
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}
