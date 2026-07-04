/**
 * Standardized Sonner Toaster configuration.
 * Position: bottom-right, richColors, auto-dismiss timers.
 * Requirements: 53.1–53.6
 */
import { Toaster as SonnerToaster } from 'sonner';

export function SonnerToasterProvider() {
  return (
    <SonnerToaster
      position="bottom-right"
      richColors
      closeButton
      expand={false}
      visibleToasts={3}
      toastOptions={{
        duration: 4000,
        classNames: {
          success: 'border-green-200',
          error: 'border-red-200',
          warning: 'border-amber-200',
          info: 'border-blue-200',
        },
      }}
    />
  );
}
