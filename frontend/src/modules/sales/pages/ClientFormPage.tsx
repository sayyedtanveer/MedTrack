/**
 * Client Form Page
 * Create or edit a sales client
 * REQ-SP-003
 */

import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { FormSkeleton } from '@/components/shared/LoadingSkeleton';
import { clientsApi, priceListsApi } from '@/services/sales.service';
import { SalesClient, CreateClientRequest, PriceList } from '@/types/sales.types';
import { ArrowLeft, Save } from 'lucide-react';

import { numberSeriesService } from '@/services/number-series.service';

const NONE_VALUE = '__none__';

const INDIAN_PHONE_REGEX = /^(?:\+91[\-\s]?)?[6789]\d{9}$/;

export default function ClientFormPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEditing = !!id;

  const [formData, setFormData] = useState<Partial<SalesClient> & CreateClientRequest>({
    code: '',
    name: '',
    email: '',
    phone: '',
    address: '',
    gst_number: '',
    credit_limit: 0,
    payment_terms_days: 0,
    default_price_list_id: null,
  });
  const [loading, setLoading] = useState(isEditing);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [previewCode, setPreviewCode] = useState<string>('');

  const emailInputRef = useRef<HTMLInputElement>(null);
  const phoneInputRef = useRef<HTMLInputElement>(null);

  // Price lists for the dropdown
  const [priceLists, setPriceLists] = useState<PriceList[]>([]);

  // Load price lists on mount (all, so inactive assignments are still visible)
  useEffect(() => {
    priceListsApi.list(200, 0)
      .then((r) => setPriceLists(r.items))
      .catch(() => {/* non-critical — dropdown just stays empty */});
  }, []);

  // Fetch number series for client (customer) code
  useEffect(() => {
    if (!isEditing) {
      numberSeriesService.previewCode('customer')
        .then((res) => {
          setPreviewCode(res.preview);
        })
        .catch(console.error);
    }
  }, [isEditing]);

  useEffect(() => {
    const loadClient = async () => {
      if (!isEditing || !id) return;
      try {
        setError(null);
        const client = await clientsApi.get(id);
        setFormData({
          ...client,
          default_price_list_id: client.default_price_list_id ?? null,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load client');
      } finally {
        setLoading(false);
      }
    };
    loadClient();
  }, [isEditing, id]);

  const handleSave = async () => {
    // Basic validations
    if (formData.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email.trim())) {
      setError("Please enter a valid email address.");
      emailInputRef.current?.focus();
      return;
    }

    if (formData.phone && !INDIAN_PHONE_REGEX.test(formData.phone.trim())) {
      setError("Please enter a valid Indian phone number (e.g., +91 9876543210 or 10 digits starting with 6-9).");
      phoneInputRef.current?.focus();
      return;
    }

    setSaving(true);
    try {
      if (isEditing && id) {
        await clientsApi.update(id, {
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
          address: formData.address,
          gst_number: formData.gst_number,
          credit_limit: formData.credit_limit,
          payment_terms_days: formData.payment_terms_days,
          default_price_list_id: formData.default_price_list_id ?? null,
        });
      } else {
        const payloadCode = formData.code?.trim();
        const codeToSend = payloadCode && payloadCode !== previewCode ? payloadCode : undefined;

        await clientsApi.create({
          ...(codeToSend ? { code: codeToSend } : {}),
          name: formData.name || '',
          email: formData.email,
          phone: formData.phone,
          address: formData.address,
          gst_number: formData.gst_number,
          credit_limit: formData.credit_limit || 0,
          payment_terms_days: formData.payment_terms_days || 0,
        });
      }
      navigate('/sales/clients');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save client');
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
        <Button variant="ghost" size="sm" onClick={() => navigate('/sales/clients')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditing ? 'Edit Client' : 'Add New Client'}
          </h1>
          <p className="text-gray-600">{isEditing ? 'Update client details' : 'Register a new sales client'}</p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Client Form */}
      <Card>
        <CardHeader>
          <CardTitle>Client Information</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Code */}
          {!isEditing && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Client Code (Auto-generated if empty)</label>
              <Input
                placeholder={previewCode || "e.g., CLI001"}
                value={formData.code || ''}
                onChange={(e) => setFormData({...formData, code: e.target.value})}
              />
            </div>
          )}

          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Client Name *</label>
            <Input
              placeholder="Full client name"
              value={formData.name || ''}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
            />
          </div>

          {/* Contact Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <Input
                ref={emailInputRef}
                type="email"
                placeholder="client@example.com"
                value={formData.email || ''}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone</label>
              <Input
                ref={phoneInputRef}
                placeholder="+91 9876543210"
                value={formData.phone || ''}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
              />
            </div>
          </div>

          {/* Address */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Address</label>
            <Textarea
              placeholder="Full address"
              value={formData.address || ''}
              onChange={(e) => setFormData({...formData, address: e.target.value})}
              rows={3}
            />
          </div>

          {/* GST & Payment */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">GST Number</label>
              <Input
                placeholder="GST ID"
                value={formData.gst_number || ''}
                onChange={(e) => setFormData({...formData, gst_number: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Payment Terms (Days)</label>
              <Input
                type="number"
                placeholder="30"
                value={formData.payment_terms_days || 0}
                onChange={(e) => setFormData({...formData, payment_terms_days: parseInt(e.target.value)})}
              />
            </div>
          </div>

          {/* Credit Limit */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Credit Limit *</label>
            <Input
              type="number"
              placeholder="10000"
              value={formData.credit_limit || 0}
              onChange={(e) => setFormData({...formData, credit_limit: parseFloat(e.target.value)})}
            />
          </div>

          {/* Default Price List — REQ-SP-003 */}
          {isEditing && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Default Price List</label>
              <Select
                value={formData.default_price_list_id ?? NONE_VALUE}
                onValueChange={(v) =>
                  setFormData({
                    ...formData,
                    default_price_list_id: v === NONE_VALUE ? null : v,
                  })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="No default price list" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NONE_VALUE}>— None —</SelectItem>
                  {priceLists.map((pl) => (
                    <SelectItem key={pl.id} value={pl.id}>
                      {pl.name}
                      {!pl.is_active && (
                        <span className="ml-2 text-xs text-amber-600">(Inactive)</span>
                      )}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-sm text-gray-500 mt-1">
                Determines which price list is used when creating sales orders for this client.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={() => navigate('/sales/clients')}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={saving} className="bg-blue-600 hover:bg-blue-700">
          <Save className="mr-2 h-4 w-4" />
          {saving ? 'Saving...' : 'Save Client'}
        </Button>
      </div>
    </div>
  );
}
