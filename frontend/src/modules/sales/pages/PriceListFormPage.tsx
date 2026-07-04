/**
 * Price List Form Page
 * Create or edit price lists
 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { TableSkeleton } from '@/components/shared/LoadingSkeleton';
import { priceListsApi } from '@/services/sales.service';
import { CreatePriceListRequest } from '@/types/sales.types';
import { ArrowLeft, Save } from 'lucide-react';

export default function PriceListFormPage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const isEditMode = Boolean(id);

  const [loading, setLoading] = useState(isEditMode);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    valid_from: new Date().toISOString().split('T')[0],
    valid_to: '',
    is_default: false,
  });

  useEffect(() => {
    if (isEditMode && id) {
      loadPriceList();
    }
  }, [id, isEditMode]);

  const loadPriceList = async () => {
    try {
      if (!id) return;
      setError(null);
      setLoading(true);
      const data = await priceListsApi.get(id);
      setFormData({
        name: data.name,
        valid_from: new Date(data.valid_from).toISOString().split('T')[0],
        valid_to: data.valid_to ? new Date(data.valid_to).toISOString().split('T')[0] : '',
        is_default: data.is_default,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load price list');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    const checked = (e.target as HTMLInputElement).checked;

    setFormData((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      setError(null);
      setSubmitting(true);

      if (!formData.name.trim()) {
        setError('Price list name is required');
        return;
      }

      const payload: CreatePriceListRequest = {
        name: formData.name,
        valid_from: formData.valid_from,
        valid_to: formData.valid_to || undefined,
        is_default: formData.is_default,
      };

      if (isEditMode && id) {
        await priceListsApi.update(id, payload);
      } else {
        await priceListsApi.create(payload);
      }

      navigate('/sales/price-lists');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save price list');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8">
        <TableSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/sales/price-lists')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {isEditMode ? 'Edit Price List' : 'New Price List'}
          </h1>
          <p className="text-gray-600 mt-1">
            {isEditMode
              ? 'Update price list details'
              : 'Create a new price list with pricing rules'}
          </p>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle>Price List Details</CardTitle>
          <CardDescription>
            Configure the pricing rules and validity period
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Name */}
            <div>
              <Label htmlFor="name">Price List Name</Label>
              <Input
                id="name"
                name="name"
                type="text"
                placeholder="e.g., Premium Clients Q2 2024"
                value={formData.name}
                onChange={handleChange}
                required
                className="mt-2"
              />
              <p className="text-sm text-gray-600 mt-1">
                A descriptive name to identify this price list
              </p>
            </div>

            {/* Validity Period */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="valid_from">Valid From</Label>
                <Input
                  id="valid_from"
                  name="valid_from"
                  type="date"
                  value={formData.valid_from}
                  onChange={handleChange}
                  required
                  className="mt-2"
                />
              </div>
              <div>
                <Label htmlFor="valid_to">Valid Until (optional)</Label>
                <Input
                  id="valid_to"
                  name="valid_to"
                  type="date"
                  value={formData.valid_to}
                  onChange={handleChange}
                  className="mt-2"
                />
                <p className="text-sm text-gray-600 mt-1">
                  Leave blank for unlimited validity
                </p>
              </div>
            </div>

            {/* Status Flags */}
            <div className="space-y-3 border-t pt-4">
                <div className="flex items-center gap-3">
                <input
                  id="is_default"
                  name="is_default"
                  type="checkbox"
                  checked={formData.is_default}
                  onChange={handleChange}
                  className="w-4 h-4 rounded border-gray-300"
                />
                <Label htmlFor="is_default" className="font-normal cursor-pointer">
                  Set as Default Price List
                </Label>
                <p className="text-sm text-gray-600">
                  (Used when no specific price list is assigned)
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 border-t pt-6">
              <Button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-2"
              >
                <Save className="h-4 w-4" />
                {submitting ? 'Saving...' : isEditMode ? 'Update Price List' : 'Create Price List'}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate('/sales/price-lists')}
                disabled={submitting}
              >
                Cancel
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="font-semibold text-blue-900 mb-2">About Price Lists</h3>
          <ul className="text-sm text-blue-800 space-y-1">
            <li>• Price lists define the pricing rules for products</li>
            <li>• You can add line items (product-price mappings) after creating the list</li>
            <li>• Only one price list can be marked as default</li>
            <li>• Active price lists are available for use in sales orders</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
