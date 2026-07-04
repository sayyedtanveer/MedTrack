/**
 * Hook to warn users about unsaved form changes before navigation.
 * Requirements: 51.5
 */
import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';

export function useUnsavedChanges(
  isDirty: boolean,
  message = 'You have unsaved changes. Leave anyway?'
) {
  // Browser beforeunload — warns when closing tab or navigating away externally
  useEffect(() => {
    if (!isDirty) return;
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = message;
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [isDirty, message]);

  // React Router navigation blocker — warns on in-app route changes
  const blocker = useBlocker(isDirty);

  return { blocker };
}
