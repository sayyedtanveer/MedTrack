/**
 * Procurement Pricing Dashboard Page
 * Unified interface for supplier agreements, cost revisions, and pricing analytics
 * Phase 2e Frontend Integration
 */

import React, { useState } from "react";
import { SupplierPriceAgreementForm } from "../components/SupplierPriceAgreementForm";
import { PendingCostRevisionsPanel } from "../components/PendingCostRevisionsPanel";
import { MaterialCostHistoryPanel } from "../components/MaterialCostHistoryPanel";
import { PriceOverridePanel } from "../components/PriceOverridePanel";
import { usePricingAgreements } from "../hooks/usePricingAgreements";
import { CreateSupplierPriceAgreementRequest } from "../types/pricing";

type TabType = "agreements" | "revisions" | "cost-history" | "price-overrides" | "create-agreement";

// State for material cost history and price overrides
interface DetailViewState {
  materialId: string | null;
  materialName: string | null;
}

export const ProcurementPricingPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>("agreements");
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [detailView, setDetailView] = useState<DetailViewState>({
    materialId: null,
    materialName: null,
  });
  const {
    agreements,
    loading: agreementsLoading,
    error: agreementsError,
    createAgreement,
    fetchAgreements,
  } = usePricingAgreements();

  // Fetch agreements on mount and when switching tabs
  React.useEffect(() => {
    if (activeTab === "agreements") {
      fetchAgreements({ page: 1, page_size: 20 });
    }
  }, [activeTab]);

  const handleCreateAgreement = async (data: CreateSupplierPriceAgreementRequest) => {
    try {
      await createAgreement(data);
      setSuccessMessage("✅ Supplier price agreement created successfully!");
      setActiveTab("agreements");
      setTimeout(() => setSuccessMessage(null), 5000);
    } catch (err) {
      console.error("Error creating agreement:", err);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Procurement Pricing Management</h1>
          <p className="text-gray-600">
            Manage supplier price agreements, standard cost revisions, and pricing analytics
          </p>
        </div>

        {/* Success Message */}
        {successMessage && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded text-green-800">
            {successMessage}
          </div>
        )}

        {/* Tab Navigation */}
        <div className="mb-6 flex gap-2 border-b border-gray-300 overflow-x-auto">
          <button
            onClick={() => setActiveTab("agreements")}
            className={`px-4 py-2 font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "agreements"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            📋 Agreements
          </button>
          <button
            onClick={() => setActiveTab("revisions")}
            className={`px-4 py-2 font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "revisions"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            💰 Cost Revisions
          </button>
          <button
            onClick={() => setActiveTab("cost-history")}
            className={`px-4 py-2 font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "cost-history"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            📈 Cost History
          </button>
          <button
            onClick={() => setActiveTab("price-overrides")}
            className={`px-4 py-2 font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "price-overrides"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            📊 Price Overrides
          </button>
          <button
            onClick={() => setActiveTab("create-agreement")}
            className={`px-4 py-2 font-semibold border-b-2 whitespace-nowrap transition-colors ${
              activeTab === "create-agreement"
                ? "border-blue-500 text-blue-600"
                : "border-transparent text-gray-600 hover:text-gray-900"
            }`}
          >
            ➕ Create Agreement
          </button>
        </div>

        {/* Content */}
        <div className="bg-white rounded-lg shadow">
          {activeTab === "agreements" && (
            <div className="p-6">
              {agreementsError && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded text-red-800">
                  Error: {agreementsError}
                </div>
              )}

              {agreementsLoading ? (
                <div className="text-center py-8 text-gray-500">Loading agreements...</div>
              ) : agreements.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">No supplier price agreements found</p>
                  <button
                    onClick={() => setActiveTab("create-agreement")}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
                  >
                    Create First Agreement
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-50 border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Supplier</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Material</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Base Price</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Effective From</th>
                        <th className="px-4 py-3 text-left font-semibold text-gray-700">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agreements.map((agreement) => (
                        <tr key={agreement.id} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="px-4 py-3 text-gray-900">{agreement.supplier_id}</td>
                          <td className="px-4 py-3 text-gray-900">{agreement.material_id}</td>
                          <td className="px-4 py-3 text-gray-900">
                            {agreement.base_price.toFixed(6)} {agreement.currency_code}
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`px-2 py-1 rounded text-xs font-semibold ${
                                agreement.status === "ACTIVE"
                                  ? "bg-green-100 text-green-800"
                                  : agreement.status === "DRAFT"
                                  ? "bg-gray-100 text-gray-800"
                                  : agreement.status === "PENDING"
                                  ? "bg-yellow-100 text-yellow-800"
                                  : agreement.status === "APPROVED"
                                  ? "bg-blue-100 text-blue-800"
                                  : "bg-red-100 text-red-800"
                              }`}
                            >
                              {agreement.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-600 text-xs">
                            {new Date(agreement.effective_from).toLocaleDateString()}
                          </td>
                          <td className="px-4 py-3">
                            <button className="text-blue-600 hover:text-blue-800 font-semibold text-sm">
                              View
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {activeTab === "revisions" && (
            <div className="p-6">
              <PendingCostRevisionsPanel
                onRevisionApproved={(revision) => {
                  setSuccessMessage(
                    `✅ Cost revision approved! Material cost updated to ₹${revision.requested_cost.toFixed(6)}`
                  );
                  setTimeout(() => setSuccessMessage(null), 5000);
                }}
                onRevisionRejected={() => {
                  setSuccessMessage(`❌ Cost revision rejected`);
                  setTimeout(() => setSuccessMessage(null), 5000);
                }}
              />
            </div>
          )}

          {activeTab === "cost-history" && (
            <div className="p-6">
              {detailView.materialId ? (
                <div>
                  <button
                    onClick={() => setDetailView({ materialId: null, materialName: null })}
                    className="mb-4 text-blue-600 hover:text-blue-800 font-semibold"
                  >
                    ← Back to List
                  </button>
                  <MaterialCostHistoryPanel
                    materialId={detailView.materialId}
                    materialName={detailView.materialName || "Material"}
                  />
                </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-600 mb-4">
                    Select a material to view its cost history
                  </p>
                  <p className="text-sm text-gray-500">
                    Cost history is typically viewed from the material detail page or by entering a material ID
                  </p>
                </div>
              )}
            </div>
          )}

          {activeTab === "price-overrides" && (
            <div className="p-6">
              <PriceOverridePanel
                materialId={detailView.materialId || undefined}
                onOverrideRecorded={() => {
                  setSuccessMessage("✅ Price override recorded successfully!");
                  setTimeout(() => setSuccessMessage(null), 5000);
                }}
              />
            </div>
          )}

          {activeTab === "create-agreement" && (
            <div className="p-6">
              <SupplierPriceAgreementForm
                onSubmit={handleCreateAgreement}
                onCancel={() => setActiveTab("agreements")}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
