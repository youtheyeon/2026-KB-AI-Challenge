import { AlertTriangle } from 'lucide-react';

interface ErrorBannerProps {
  message: string;
}

export const ErrorBanner = ({ message }: ErrorBannerProps) => (
  <div className="flex items-start gap-2 rounded border border-red-200 bg-red-50 px-4 py-3 text-xs text-red-600">
    <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
    {message}
  </div>
);
