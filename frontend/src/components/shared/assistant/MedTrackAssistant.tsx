import { AssistantGuidance } from "./AssistantTypes";
import { WorkflowProgress } from "./WorkflowProgress";
import { NextActionCard } from "./NextActionCard";
import { WorkflowWarnings } from "./WorkflowWarnings";

interface MedTrackAssistantProps {
  guidance: AssistantGuidance | null;
}

export function MedTrackAssistant({ guidance }: MedTrackAssistantProps) {
  if (!guidance) return null;

  return (
    <div className="flex flex-col gap-1 mb-8">
      {/* Visual Journey Tracker */}
      <WorkflowProgress guidance={guidance} />
      
      {/* Warnings that block progress */}
      <WorkflowWarnings guidance={guidance} />
      
      {/* The rich Success / What's Next card */}
      <NextActionCard guidance={guidance} />
    </div>
  );
}
