import React, { useState, useEffect } from 'react';
import { useAuthStore } from '../../../app/store/authStore';
import { AlertCircle, Check, Lock, Shield } from 'lucide-react';
import TwoFactorSetup from '../../auth/pages/TwoFactorSetup';
import ChangePasswordModal from '../../auth/components/ChangePasswordModal';
import api from '../../../services/api-client';

export const SecuritySettingsPage: React.FC = () => {
  const { user: _user } = useAuthStore();
  const [twoFAEnabled, setTwoFAEnabled] = useState(false);
  const [loading, setLoading] = useState(true);
  const [showTwoFASetup, setShowTwoFASetup] = useState(false);
  const [showChangePassword, setShowChangePassword] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Fetch current 2FA status
  useEffect(() => {
    const fetchTwoFAStatus = async () => {
      try {
        const response = await api.get('/auth/me');
        setTwoFAEnabled(response.data.totp_enabled || false);
        setLoading(false);
      } catch (err) {
        console.error('Failed to fetch 2FA status:', err);
        setLoading(false);
      }
    };
    fetchTwoFAStatus();
  }, []);

  const handleDisable2FA = async () => {
    if (!window.confirm('Are you sure? You will need to re-enable 2FA later.')) return;
    try {
      setLoading(true);
      await api.post('/auth/2fa/disable', {
        password: window.prompt('Enter your password to disable 2FA:'),
      });
      setTwoFAEnabled(false);
      setSuccessMessage('2FA has been disabled successfully.');
      setTimeout(() => setSuccessMessage(''), 3000);
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Failed to disable 2FA');
      setTimeout(() => setErrorMessage(''), 3000);
    } finally {
      setLoading(false);
    }
  };

  const handleSetupComplete = () => {
    setTwoFAEnabled(true);
    setShowTwoFASetup(false);
    setSuccessMessage('2FA has been enabled successfully.');
    setTimeout(() => setSuccessMessage(''), 3000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin">
          <Shield className="w-6 h-6" />
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl">
      <div className="space-y-6">
        {/* Page Header */}
        <div className="border-b border-border pb-6">
          <h1 className="text-2xl font-bold text-foreground">Security Settings</h1>
          <p className="text-muted-foreground mt-2">Manage your account security and authentication</p>
        </div>

        {/* Success/Error Messages */}
        {successMessage && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800">
            <Check className="w-5 h-5 text-green-600 dark:text-green-400" />
            <span className="text-green-700 dark:text-green-300">{successMessage}</span>
          </div>
        )}
        {errorMessage && (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <span className="text-red-700 dark:text-red-300">{errorMessage}</span>
          </div>
        )}

        {/* Two-Factor Authentication Section */}
        <div className="rounded-lg border border-border p-6 bg-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Lock className="w-5 h-5 text-primary" />
              <div>
                <h2 className="text-lg font-semibold text-card-foreground">Two-Factor Authentication (2FA)</h2>
                <p className="text-sm text-muted-foreground mt-1">Add an extra layer of security to your account</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${
                twoFAEnabled
                  ? 'bg-green-100 dark:bg-green-900 text-green-800 dark:text-green-200'
                  : 'bg-muted text-muted-foreground'
              }`}>
                {twoFAEnabled ? '✓ Enabled' : 'Disabled'}
              </div>
            </div>
          </div>
          <div className="space-y-4">
            <div className="p-4 rounded-lg bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-900 dark:text-blue-300">
                <strong>What is 2FA?</strong> Two-factor authentication requires you to provide two different types of information to log in - your password and a code from an authenticator app.
              </p>
            </div>
            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground">
                Current Status: <span className={twoFAEnabled ? 'text-green-600 dark:text-green-400' : 'text-muted-foreground'}>
                  {twoFAEnabled ? 'Enabled' : 'Not Enabled'}
                </span>
              </p>
              <p className="text-sm text-muted-foreground">
                {twoFAEnabled
                  ? 'Your account is protected with 2FA. You can disable it below if needed.'
                  : 'Enable 2FA to secure your account with an authenticator app.'}
              </p>
            </div>
            <div className="flex gap-3 pt-2">
              {!twoFAEnabled ? (
                <button onClick={() => setShowTwoFASetup(true)}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 font-medium text-sm transition">
                  Enable 2FA
                </button>
              ) : (
                <button onClick={handleDisable2FA} disabled={loading}
                  className="px-4 py-2 bg-destructive/10 text-destructive border border-destructive/20 rounded-lg hover:bg-destructive/20 font-medium text-sm transition disabled:opacity-50">
                  {loading ? 'Disabling...' : 'Disable 2FA'}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Password & Session Management */}
        <div className="rounded-lg border border-border p-6 bg-card">
          <h3 className="text-lg font-semibold text-card-foreground mb-4">Password & Session Management</h3>
          <div className="space-y-3">
            <button onClick={() => setShowChangePassword(true)}
              className="w-full text-left px-4 py-3 rounded-lg border border-border hover:bg-accent transition text-foreground font-medium">
              Change Password
            </button>
            <button className="w-full text-left px-4 py-3 rounded-lg border border-border hover:bg-accent transition text-foreground font-medium">
              View Active Sessions
            </button>
            <button className="w-full text-left px-4 py-3 rounded-lg border border-border hover:bg-accent transition text-foreground font-medium">
              Login Activity
            </button>
          </div>
        </div>

        {/* 2FA Setup Modal */}
        {showTwoFASetup && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
            <div className="bg-card rounded-lg max-w-2xl w-full max-h-96 overflow-auto">
              <div className="p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-foreground">Enable Two-Factor Authentication</h3>
                  <button onClick={() => setShowTwoFASetup(false)} className="text-muted-foreground hover:text-foreground">✕</button>
                </div>
                <TwoFactorSetup onComplete={handleSetupComplete} />
              </div>
            </div>
          </div>
        )}
        <ChangePasswordModal isOpen={showChangePassword} onClose={() => setShowChangePassword(false)} />
      </div>
    </div>
  );
};

export default SecuritySettingsPage;
