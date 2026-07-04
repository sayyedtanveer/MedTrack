/**
 * Component variant standards documentation.
 * Requirements: 50.1–50.5
 *
 * These match the shadcn/ui cva() definitions already in use.
 * Document here for reference and consistency enforcement.
 */

export const buttonVariants = {
  variants: ['default', 'destructive', 'outline', 'secondary', 'ghost', 'link'],
  sizes: ['default', 'sm', 'lg', 'icon'],
} as const;

export const badgeVariants = {
  variants: ['default', 'secondary', 'destructive', 'outline'],
} as const;

export const inputStates = {
  default: 'border-input',
  focused: 'ring-2 ring-ring ring-offset-2',
  error: 'border-destructive focus:ring-destructive',
  disabled: 'cursor-not-allowed opacity-50',
} as const;

export const cardVariants = {
  default: 'rounded-lg border bg-card shadow-sm',
  elevated: 'rounded-lg border bg-card shadow-md',
  interactive: 'rounded-lg border bg-card shadow-sm cursor-pointer hover:shadow-md transition-shadow',
} as const;

// Type helpers for consumers
export type ButtonVariant = (typeof buttonVariants.variants)[number];
export type ButtonSize = (typeof buttonVariants.sizes)[number];
export type BadgeVariant = (typeof badgeVariants.variants)[number];
export type InputState = keyof typeof inputStates;
export type CardVariant = keyof typeof cardVariants;
