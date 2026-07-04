/**
 * Price Lists Page
 * Manage price lists and pricing
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TableSkeleton } from '@/components/shared/LoadingSkeleton';
import { priceListsApi } from '@/services/sales.service';
import { PriceList } from '@/types/sales.types';
import { Plus, Edit2, IndianRupee } from 'lucide-react';
import { formatCurrency } from '@/utils/currency';

export default function PriceListsPage() {
  const navigate = useNavigate();
  const [priceLists, setPriceLists] = useState<PriceList[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  useEffect(() => {
    const loadPriceLists = async () => {
      try {
        setError(null);
        setLoading(true);
        const offset = (currentPage - 1) * pageSize;
        const response = await priceListsApi.list(pageSize, offset);
        setPriceLists(response.items);
        setTotal(response.total);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load price lists');
      } finally {
        setLoading(false);
      }
    };

    loadPriceLists();
  }, [currentPage, pageSize]);

  if (loading && priceLists.length === 0) {
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
          <h1 className="text-3xl font-bold text-gray-900">Price Lists</h1>
          <p className="text-gray-600 mt-1">Configure product pricing and rates</p>
        </div>
        <Button size="lg" onClick={() => navigate('/sales/price-lists/new')}>
          <Plus className="mr-2 h-4 w-4" />
          New Price List
        </Button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Price Lists */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {priceLists.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="pt-12 text-center text-gray-500 pb-12">
              <IndianRupee className="h-12 w-12 mx-auto mb-4 text-gray-400" />
              <p>No price lists created yet</p>
              <Button variant="link" className="mt-2">
                Create First Price List
              </Button>
            </CardContent>
          </Card>
        ) : (
          priceLists.map((priceList) => (
            <Card key={priceList.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{priceList.name}</CardTitle>
                    <CardDescription>
                      {priceList.lines.length} line items
                    </CardDescription>
                  </div>
                  <div className="flex gap-2">
                    {priceList.is_default && (
                      <Badge className="bg-blue-100 text-blue-800">Default</Badge>
                    )}
                    {priceList.is_active && (
                      <Badge className="bg-green-100 text-green-800">Active</Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-gray-600">Valid From:</span>
                    <p className="font-medium">
                      {new Date(priceList.valid_from).toLocaleDateString()}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-600">Valid To:</span>
                    <p className="font-medium">
                      {priceList.valid_to ? new Date(priceList.valid_to).toLocaleDateString() : 'No limit'}
                    </p>
                  </div>
                </div>

                {/* Price List Lines Preview */}
                {priceList.lines.length > 0 && (
                  <div className="border-t pt-3 mt-3">
                    <p className="text-xs font-semibold text-gray-600 mb-2">Sample Prices:</p>
                    <div className="space-y-1">
                      {priceList.lines.slice(0, 3).map((line) => (
                        <div key={line.id} className="flex justify-between text-xs text-gray-700">
                          <span>{line.product_id}</span>
                          <span className="font-semibold">{formatCurrency(line.unit_price)}</span>
                        </div>
                      ))}
                      {priceList.lines.length > 3 && (
                        <p className="text-xs text-gray-500 pt-1">
                          +{priceList.lines.length - 3} more items
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full mt-4"
                  onClick={() => navigate(`/sales/price-lists/${priceList.id}/edit`)}
                >
                  <Edit2 className="mr-2 h-4 w-4" />
                  Edit Price List
                </Button>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex justify-between items-center py-4 border-t">
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
    </div>
  );
}
