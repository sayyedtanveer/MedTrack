import { AssistantGuidance, IAssistantProvider } from '@/components/shared/assistant/AssistantTypes';
import { SalesProvider } from './providers/SalesProvider';
import { ProcurementProvider } from './providers/ProcurementProvider';
import { ManufacturingProvider } from './providers/ManufacturingProvider';
import { QualityProvider } from './providers/QualityProvider';
import { InventoryProvider } from './providers/InventoryProvider';
import { DispatchProvider } from './providers/DispatchProvider';

export class AssistantEngine {
  private static providers: IAssistantProvider<any>[] = [
    new SalesProvider(),
    new ProcurementProvider(),
    new ManufacturingProvider(),
    new QualityProvider(),
    new InventoryProvider(),
    new DispatchProvider()
  ];

  /**
   * Main entry point for the MedTrack Assistant.
   * Loops through all registered providers and returns guidance from the first one that can handle the entity.
   */
  static getGuidance(document: any): AssistantGuidance | null {
    if (!document) return null;

    for (const provider of this.providers) {
      if (provider.canHandle(document)) {
        return provider.getGuidance(document);
      }
    }
    
    return null;
  }
}
