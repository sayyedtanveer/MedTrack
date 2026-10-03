/**
 * Sales Order Form Page
 * Create or edit a sales order
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { FormSkeleton } from '@/components/shared/LoadingSkeleton';
import { ordersApi, clientsApi } from '@/services/sales.service';
import { SalesOrder, SalesClient, OrderPriority } from '@/types/sales.types';
import { ArrowLeft, Save } from 'lucide-react';

const PRIORITIES: OrderPriority[] = ['LOW', 'NORMAL', 'HIGH', 'URGENT'];

const PRIORITY_COLORS: Record<OrderPriority, string> = {
  LOW: 'text-slate-500',
  NORMAL: 'text-slate-700',
  HIGH: 'text-amber-600',
  URGENT: 'text-red-600',
};

export default function SalesOrderFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [order, setOrder] = useState<Partial<SalesOrder>>({
    client_id: '',
    order_date: new Date().toISOString().split('T')[0],
    delivery_date: '',
    priority: 'NORMAL', // Default priority
    notes: '',
    lines: [],
  });
  const [clients, setClients] = useState<SalesClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        setError(null);
        const clientsResponse = await clientsApi.list(100);
        setClients(clientsResponse.items);

        if (isEditing && id) {
          const orderData = await ordersApi.get(id);
          setOrder(orderData);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load data');
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [isEditing, id]);

  const handleSave = async () => {
    if (!order.client_id) {
      setError('Please select a client');
      return;
    }

    setSaving(true);
    try {
      if (isEditing && id) {
        await ordersApi.update(id, {
          delivery_date: order.delivery_date || '',
          notes: order.notes,
        });
      } else {
        await ordersApi.create({
          client_id: order.client_id,
          order_date: order.order_date || '',
          delivery_date: order.delivery_date || '',
          priority: order.priority || 'NORMAL',
          notes: order.notes || '',
        });
      }
      navigate('/sales/orders');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save order');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <FormSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" onClick={() => navigate('/sales/orders')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? 'Edit Order' : 'Create New Order'}
          </h1>
          <p className="text-gray-600">{isEditing ? 'Update order details' : 'Add a new sales order'}</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Order Form */}
      <Card>
        <CardHeader>
          <CardTitle>Order Details</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Client Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Client *</label>
            <Select 
              value={order.client_id || 'select'} 
              onValueChange={(v) => setOrder({...order, client_id: v === 'select' ? '' : v})}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select a client" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="select" disabled>Select a client</SelectItem>
                {clients && clients.map((client) => (
                  <SelectItem key={client.id} value={client.id}>
                    {client.name} ({client.code})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dates */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Order Date *</label>
              <Input
                type="date"
                value={order.order_date?.split('T')[0] || ''}
                onChange={(e) => setOrder({...order, order_date: e.target.value})}
                disabled={isEditing}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Delivery Date *</label>
              <Input
                type="date"
                value={order.delivery_date?.split('T')[0] || ''}
                onChange={(e) => setOrder({...order, delivery_date: e.target.value})}
              />
            </div>
          </div>

          {/* Priority Selection */}
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Order Priority
                <span className="ml-2 text-xs text-gray-500 font-normal">
                  (Auto-created work orders will inherit this priority)
                </span>
              </label>
              <div className="grid gap-2 sm:grid-cols-4">
                {PRIORITIES.map((priority) => (
                  <button
                    type="button"
                    key={priority}
                    onClick={() => setOrder({...order, priority})}
                    className={`rounded-lg border px-3 py-2 text-sm font-medium transition-colors ${
                      order.priority === priority
                        ? 'border-blue-600 bg-blue-600 text-white shadow-sm'
                        : 'border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <span className={order.priority === priority ? '' : PRIORITY_COLORS[priority]}>
                      {priority}
                    </span>
                  </button>
                ))}
              </div>
              <p className="mt-2 text-xs text-gray-500">
                <strong>URGENT:</strong> Rush orders, critical deadlines • 
                <strong className="ml-2">HIGH:</strong> Important customers • 
                <strong className="ml-2">NORMAL:</strong> Standard orders • 
                <strong className="ml-2">LOW:</strong> Flexible deadlines
              </p>
            </div>
          )}

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Notes</label>
            <Textarea
              placeholder="Additional order notes..."
              value={order.notes || ''}
              onChange={(e) => setOrder({...order, notes: e.target.value})}
              rows={4}
            />
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={() => navigate('/sales/orders')}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
          <Save className="mr-2 h-4 w-4" />
          {saving ? 'Saving...' : 'Save Order'}
        </Button>
      </div>
    </div>
  );
}
