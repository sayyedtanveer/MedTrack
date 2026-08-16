/**
 * Clients List Page
 * Display all sales clients with management options
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { TableSkeleton } from '@/components/shared/LoadingSkeleton';
import { clientsApi } from '@/services/sales.service';
import { usersService } from '@/services/users.service';
import { SalesClient } from '@/types/sales.types';
import type { User } from '@/types/auth.types';
import { Plus, Edit2, IndianRupee, KeyRound, Copy, Check } from 'lucide-react';
import { formatCurrency } from '@/utils/currency';
import { useToast } from '@/hooks/use-toast';
import { useAuthStore } from '@/app/store/authStore';
import { Dialog, DialogContent, DialogTrigger } from '@/components/ui/dialog';
import { MasterDataImportWizard } from '@/components/data/MasterDataImportWizard';
import { Upload, Download } from 'lucide-react';
import apiClient from '@/services/api-client';

type PortalCredentials = {
  email: string;
  password: string;
};

const clientUserName = (client: SalesClient) => {
  const parts = client.name.split(/\s+/).filter(Boolean);
  return {
    first_name: parts[0] || 'Client',
    last_name: parts.slice(1).join(' ') || 'Portal',
  };
};

export default function ClientsListPage() {
  const navigate = useNavigate();
  const { toast } = useToast();
  const tenantId = useAuthStore((state) => state.tenant_id);
  const clientLoginUrl = `${window.location.origin}/client/login`;
  const [clients, setClients] = useState<SalesClient[]>([]);
  const [clientUsers, setClientUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);
  const [portalCredentials, setPortalCredentials] = useState<PortalCredentials | null>(null);
  const [copiedCredentials, setCopiedCredentials] = useState(false);
  const [portalSavingClientId, setPortalSavingClientId] = useState<string | null>(null);
  const [showImportDialog, setShowImportDialog] = useState(false);

  const handleExport = async () => {
    try {
      const response = await apiClient.get('/clients/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'clients_export.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err: any) {
      toast({ title: 'Export failed', description: err.message, variant: 'destructive' });
    }
  };

  useEffect(() => {
    const loadClients = async () => {
      try {
        setError(null);
        setLoading(true);
        const offset = (currentPage - 1) * pageSize;
        const response = await clientsApi.list(pageSize, offset, search);
        setClients(response.items);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load clients');
      } finally {
        setLoading(false);
      }
    };

    loadClients();
  }, [currentPage, pageSize, search]);

  useEffect(() => {
    usersService
      .getUsers({ role: 'client' })
      .then(setClientUsers)
      .catch(() => toast({ title: 'Failed to load client portal users', variant: 'destructive' }));
  }, [toast]);

  const refreshClientUsers = async () => {
    setClientUsers(await usersService.getUsers({ role: 'client' }));
  };

  const clientUserByClientId = new Map(
    clientUsers
      .filter((user) => user.client_id)
      .map((user) => [user.client_id as string, user])
  );

  const copyPortalCredentials = async () => {
    if (!portalCredentials) return;

    await navigator.clipboard.writeText(
      [
        'Client portal login',
        `URL: ${clientLoginUrl}`,
        `Email: ${portalCredentials.email}`,
        tenantId ? `Tenant ID: ${tenantId}` : null,
        `Temporary password: ${portalCredentials.password}`,
      ].filter(Boolean).join('\n')
    );
    setCopiedCredentials(true);
    setTimeout(() => setCopiedCredentials(false), 2000);
  };

  const createPortalLogin = async (client: SalesClient) => {
    if (!client.email) {
      toast({ title: 'Client email is required before creating portal login', variant: 'destructive' });
      return;
    }

    const names = clientUserName(client);
    try {
      setPortalSavingClientId(client.id);
      const createdUser = await usersService.createUser({
        email: client.email,
        first_name: names.first_name,
        last_name: names.last_name,
        role: 'client',
        client_id: client.id,
        is_active: true,
      });

      if (createdUser.temporary_password) {
        setPortalCredentials({
          email: createdUser.email,
          password: createdUser.temporary_password,
        });
      }
      await refreshClientUsers();
      toast({
        title: 'Client portal login created',
        description: 'Copy the temporary password and share it securely with the client.',
      });
    } catch (error: any) {
      toast({
        title: 'Portal login failed',
        description: error?.response?.data?.detail || error?.message || 'Unable to create client portal login',
        variant: 'destructive',
      });
    } finally {
      setPortalSavingClientId(null);
    }
  };

  const resetPortalPassword = async (client: SalesClient, clientUser: User) => {
    try {
      setPortalSavingClientId(client.id);
      const response = await usersService.resetTemporaryPassword(clientUser.id);
      setPortalCredentials({
        email: response.email,
        password: response.temporary_password,
      });
      toast({
        title: 'Temporary password regenerated',
        description: "Copy it now. The client's previous password will no longer work.",
      });
    } catch (error: any) {
      toast({
        title: 'Password reset failed',
        description: error?.response?.data?.detail || error?.message || 'Unable to reset client password',
        variant: 'destructive',
      });
    } finally {
      setPortalSavingClientId(null);
    }
  };

  const getCreditUsagePercent = (client: SalesClient) => {
    if (client.credit_limit === 0) return 0;
    return (client.credit_used / client.credit_limit) * 100;
  };

  const getCreditColor = (percent: number) => {
    if (percent < 50) return 'bg-green-50 text-green-700 border-green-200';
    if (percent < 80) return 'bg-yellow-50 text-yellow-700 border-yellow-200';
    return 'bg-red-50 text-red-700 border-red-200';
  };

  if (loading && clients.length === 0) {
    return (
      <div className="p-8">
        <TableSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Sales Clients</h1>
          <p className="text-gray-600 mt-1">Manage client information and credit limits</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handleExport}>
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
          
          <Dialog open={showImportDialog} onOpenChange={setShowImportDialog}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Upload className="mr-2 h-4 w-4" />
                Import
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <MasterDataImportWizard 
                moduleName="clients"
                apiPrefix="/clients"
                onCancel={() => setShowImportDialog(false)}
                onComplete={() => {
                  setShowImportDialog(false);
                  setCurrentPage(1);
                  // Trigger reload
                  clientsApi.list(pageSize, 0, search).then((res) => {
                    setClients(res.items);
                    setTotal(res.total);
                  });
                }}
              />
            </DialogContent>
          </Dialog>

          <Button onClick={() => navigate('/sales/clients/new')} size="lg">
            <Plus className="mr-2 h-4 w-4" />
            New Client
          </Button>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="pt-6">
          <Input
            placeholder="Search by name or code..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
          />
        </CardContent>
      </Card>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {portalCredentials && (
        <Alert className="border-green-200 bg-green-50 text-green-950">
          <KeyRound className="h-4 w-4" />
          <AlertTitle>Client portal credentials ready</AlertTitle>
          <AlertDescription>
            <div className="mt-2 space-y-2">
              <p>The password is shown only once. Copy and share it securely with the client.</p>
              <div className="rounded-md border bg-white p-3 text-sm">
                <div>
                  <span className="font-medium">Login URL:</span>{' '}
                  <a className="text-blue-700 underline" href="/client/login">
                    {clientLoginUrl}
                  </a>
                </div>
                <div>
                  <span className="font-medium">Email:</span> {portalCredentials.email}
                </div>
                {tenantId && (
                  <div>
                    <span className="font-medium">Tenant ID:</span> {tenantId}
                  </div>
                )}
                <div>
                  <span className="font-medium">Temporary password:</span>{' '}
                  <code>{portalCredentials.password}</code>
                </div>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={copyPortalCredentials}>
                {copiedCredentials ? <Check className="mr-2 h-4 w-4" /> : <Copy className="mr-2 h-4 w-4" />}
                {copiedCredentials ? 'Copied' : 'Copy credentials'}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      )}

      {/* Clients Table */}
      <Card>
        <CardHeader>
          <CardTitle>Clients</CardTitle>
          <CardDescription>Showing {clients.length} of {total} clients</CardDescription>
        </CardHeader>
        <CardContent>
          {clients.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>No clients found</p>
              <Button
                variant="link"
                onClick={() => navigate('/sales/clients/new')}
                className="mt-2"
              >
                Add First Client
              </Button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Code</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Name</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Email</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Credit Usage</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Portal Access</th>
                    <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                    <th className="px-4 py-3 text-right font-semibold text-gray-700">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {clients.map((client) => {
                    const usagePercent = getCreditUsagePercent(client);
                    const clientUser = clientUserByClientId.get(client.id);
                    const portalActionLoading = portalSavingClientId === client.id;
                    return (
                      <tr key={client.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{client.code}</td>
                        <td className="px-4 py-3">{client.name}</td>
                        <td className="px-4 py-3 text-gray-600">{client.email || '-'}</td>
                        <td className="px-4 py-3">
                          <div className={`inline-block px-3 py-1 rounded-full border text-sm ${getCreditColor(usagePercent)}`}>
                            <IndianRupee className="inline h-3 w-3 mr-1" />
                            {formatCurrency(client.credit_used)} / {formatCurrency(client.credit_limit)}
                            ({usagePercent.toFixed(0)}%)
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          {clientUser ? (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => resetPortalPassword(client, clientUser)}
                              disabled={portalActionLoading}
                            >
                              <KeyRound className="mr-2 h-4 w-4" />
                              {portalActionLoading ? 'Generating...' : 'Reset password'}
                            </Button>
                          ) : (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => createPortalLogin(client)}
                              disabled={portalActionLoading || !client.email}
                            >
                              <KeyRound className="mr-2 h-4 w-4" />
                              {portalActionLoading ? 'Creating...' : 'Create login'}
                            </Button>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge className={client.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}>
                            {client.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </td>
                        <td className="px-4 py-3 text-right space-x-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => navigate(`/sales/clients/${client.id}/edit`)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {total > pageSize && (
            <div className="flex justify-between items-center mt-4 pt-4 border-t">
              <span className="text-sm text-gray-600">
                Page {currentPage} of {Math.ceil(total / pageSize)}
              </span>
              <div className="space-x-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={currentPage >= Math.ceil(total / pageSize)}
                  onClick={() => setCurrentPage(currentPage + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
