import React from "react";
import { MaterialBuyTab } from "@/modules/inventory/components/MaterialBuyTab";

/**
 * Material Buy Page
 * Dedicated page for cost governance workflow
 * Displays materials grouped by cost status and allows proposing new costs
 */
export const MaterialBuyPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Page Header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <h1 className="text-3xl font-bold text-gray-900">Material Cost Management</h1>
          <p className="mt-2 text-gray-600">
            Manage material costs, propose new prices, and track approval status
          </p>
        </div>
      </div>

      {/* Page Content */}
      <div className="max-w-7xl mx-auto">
        <MaterialBuyTab />
      </div>
    </div>
  );
};

export default MaterialBuyPage;
