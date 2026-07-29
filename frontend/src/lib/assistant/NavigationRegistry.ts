export interface NavigationDestination {
  module: string;
  destination: string;
  id?: string;
}

export class NavigationRegistry {
  /**
   * Resolves an abstract destination into a concrete hard URL.
   */
  static resolveUrl(dest: NavigationDestination): string | null {
    const key = `${dest.module.toLowerCase()}.${dest.destination.toLowerCase()}`;
    
    switch (key) {
      // Sales Routes
      case 'sales.dispatchqueue':
        return '/delivery/dispatch-queue';
      case 'sales.salesorders':
        return '/sales/orders';
      case 'sales.salesorderdetail':
        return dest.id ? `/sales/orders/${dest.id}` : null;
        
      // Manufacturing Routes
      case 'manufacturing.workorders':
        return '/manufacturing/work-orders';
      case 'manufacturing.workorderdetail':
        return dest.id ? `/manufacturing/work-orders/${dest.id}` : null;
        
      // Procurement Routes
      case 'procurement.purchaseorders':
        return '/procurement/purchase-orders';
      case 'procurement.grn_new':
        return dest.id ? `/procurement/grn?poId=${dest.id}` : '/procurement/grn';
        
      // Quality Routes
      case 'quality.dashboard':
        return dest.id ? `/dashboard/qc?wo=${dest.id}` : '/dashboard/qc';
        
      // Delivery Routes
      case 'delivery.dispatchqueue':
        return '/delivery/dispatch-queue';
        
      // Inventory Routes
      case 'inventory.storekeeper':
        return '/dashboard/storekeeper';
        
      default:
        console.warn(`NavigationRegistry: Unknown destination [${key}]`);
        return null;
    }
  }
}
