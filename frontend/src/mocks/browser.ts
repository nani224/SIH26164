import { setupWorker } from 'msw/browser';
import { handlers } from './handlers';

export const worker = typeof window !== 'undefined' ? setupWorker(...handlers) : null;
