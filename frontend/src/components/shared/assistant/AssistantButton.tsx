import { Button, ButtonProps } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import React from "react";

export interface AssistantButtonProps extends ButtonProps {
  pulse?: boolean;
}

/**
 * A wrapper around the base design system Button.
 * Use this for any action buttons that should hook into the Workflow Guidance System.
 */
export const AssistantButton = React.forwardRef<HTMLButtonElement, AssistantButtonProps>(
  ({ pulse, className, ...props }, ref) => {
    return (
      <Button
        ref={ref}
        className={cn(className, pulse && "erp-button-pulse")}
        {...props}
      />
    );
  }
);
AssistantButton.displayName = "AssistantButton";
