import { AssistantGuidance } from '@/components/shared/assistant/AssistantTypes';
import { AssistantEngine } from '../AssistantEngine';

export class InboxProvider {
  /**
   * Aggregates guidance from all other providers and sorts them by priority and due date.
   * Filters out items not relevant to the user's role.
   */
  static getInbox(entities: any[], userRoles: string[]): AssistantGuidance[] {
    const allGuidance: AssistantGuidance[] = [];

    // 1. Collect guidance for all entities
    for (const entity of entities) {
      const guidance = AssistantEngine.getGuidance(entity);
      if (guidance) {
        allGuidance.push(guidance);
      }
    }

    // 2. Filter by roles
    // An admin or tenant_admin sees everything.
    const isAdmin = userRoles.includes('ADMIN') || userRoles.includes('TENANT_ADMIN');
    
    const filtered = isAdmin ? allGuidance : allGuidance.filter(g => {
      if (!g.roles || g.roles.length === 0) return true; // If no roles defined, assume visible to all
      // Convert standard App roles to lowercase for easy matching if needed, or assume exact match
      const normalizedUserRoles = userRoles.map(r => r.toLowerCase());
      return g.roles.some(r => normalizedUserRoles.includes(r.toLowerCase()));
    });

    // 3. Sort by Priority, then Due Date
    const priorityWeight: Record<string, number> = {
      'critical': 5,
      'high': 4,
      'medium': 3,
      'low': 2,
      'info': 1
    };

    filtered.sort((a, b) => {
      const pA = priorityWeight[a.priority] || 0;
      const pB = priorityWeight[b.priority] || 0;
      
      if (pA !== pB) return pB - pA; // Descending priority

      // If priorities match, sort by due date (older dates first, i.e., overdue is highest)
      if (a.dueDate && b.dueDate) {
        return new Date(a.dueDate).getTime() - new Date(b.dueDate).getTime();
      }
      
      // Items with a due date come before items without
      if (a.dueDate) return -1;
      if (b.dueDate) return 1;

      return 0;
    });

    return filtered;
  }
}
