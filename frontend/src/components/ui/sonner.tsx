/**
 * Standardized Sonner Toaster configuration.
 * Position: top-center so errors are immediately visible.
 */
import { Toaster as SonnerToaster } from 'sonner';

export function SonnerToasterProvider() {
  return (
    <SonnerToaster
      position="top-center"
      richColors
      closeButton
      expand={false}
      visibleToasts={1}
      toastOptions={{
        duration: 4000,
        classNames: {
          error: 'border-red-200 text-sm',
        },
      }}
    />
  );
}
