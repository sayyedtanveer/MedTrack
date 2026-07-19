import { ReactNode, useState } from "react"
import {
  BookOpen,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  ArrowRight,
  Lightbulb,
  HelpCircle,
  X,
  GraduationCap,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

// ── Types ─────────────────────────────────────────────────────────────────────

export interface FieldGuideEntry {
  field: string
  purpose: string
  meaning: string
  example?: string
  recommended?: string
  bestPractice?: string
}

export interface ButtonGuideEntry {
  button: string
  what: string
  continues: string
  reversible: boolean
  affectsInventory?: boolean
}

export interface FlowStep {
  label: string
  description?: string
  active?: boolean
}

export interface FAQ {
  question: string
  answer: string
}

export interface BusinessAssistantConfig {
  /** Page title shown in the panel header */
  pageTitle: string
  /** 1–3 sentence summary of what the page is */
  about: string
  /** Business value paragraph */
  businessPurpose: string
  /** Where this page sits in the ERP flow */
  erpFlow: FlowStep[]
  /** Quick capability checklist */
  canDo: string[]
  /** Section-level walkthrough items */
  screenWalkthrough: Array<{ section: string; purpose: string; impact: string }>
  /** Field-by-field guide */
  fieldGuide: FieldGuideEntry[]
  /** Button explanations */
  buttonGuide: ButtonGuideEntry[]
  /** Prerequisites to have in place */
  beforeYouStart: string[]
  /** What happens after saving */
  afterSave: FlowStep[]
  /** Best practice bullets */
  bestPractices: string[]
  /** Common mistake bullets */
  commonMistakes: string[]
  /** Related screen links */
  relatedScreens: Array<{ label: string; href: string }>
  faqs: FAQ[]
  tips: string[]
  warnings: string[]
  successResult: string[]
}

// ── Sub-components ────────────────────────────────────────────────────────────

function SectionLabel({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <p className={cn("mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-600", className)}>
      {children}
    </p>
  )
}

function FlowDiagram({ steps }: { steps: FlowStep[] }) {
  return (
    <div className="space-y-1">
      {steps.map((step, i) => (
        <div key={i} className="flex flex-col items-start">
          <div
            className={cn(
              "rounded-lg px-3 py-1.5 text-xs font-medium transition-colors w-full",
              step.active
                ? "bg-blue-600 text-white shadow-sm"
                : "bg-slate-100 text-slate-700"
            )}
          >
            {step.label}
            {step.description && (
              <p className="mt-0.5 text-[11px] font-normal opacity-80">{step.description}</p>
            )}
          </div>
          {i < steps.length - 1 && (
            <div className="ml-3 flex h-4 items-center">
              <ChevronRight className="h-3 w-3 rotate-90 text-slate-400" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function CheckList({ items, variant = "success" }: { items: string[]; variant?: "success" | "warning" | "info" }) {
  const colors = {
    success: "text-emerald-600",
    warning: "text-amber-600",
    info: "text-blue-600",
  }
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
          <CheckCircle2 className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", colors[variant])} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function WarningList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-500" />
          <span className="text-amber-800">{item}</span>
        </li>
      ))}
    </ul>
  )
}

function TipList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-xs text-slate-700">
          <Lightbulb className="mt-0.5 h-3.5 w-3.5 shrink-0 text-yellow-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

function FieldGuideCard({ entry }: { entry: FieldGuideEntry }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 space-y-1.5">
      <div className="flex items-center gap-2">
        <Badge variant="secondary" className="text-[10px] font-mono px-1.5 py-0">
          {entry.field}
        </Badge>
      </div>
      <p className="text-xs font-medium text-slate-900">{entry.purpose}</p>
      <p className="text-xs text-slate-600">{entry.meaning}</p>
      {entry.example && (
        <p className="text-xs text-slate-500">
          <span className="font-medium">Example: </span>
          <code className="rounded bg-white border border-slate-200 px-1.5 py-0.5 font-mono text-[11px]">
            {entry.example}
          </code>
        </p>
      )}
      {entry.recommended && (
        <p className="text-xs text-slate-500">
          <span className="font-medium">Recommended: </span>{entry.recommended}
        </p>
      )}
      {entry.bestPractice && (
        <p className="text-xs text-blue-700 bg-blue-50 rounded px-2 py-1">
          💡 {entry.bestPractice}
        </p>
      )}
    </div>
  )
}

function ButtonGuideCard({ entry }: { entry: ButtonGuideEntry }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 space-y-1.5">
      <div className="flex items-center justify-between">
        <Badge className="text-[10px] px-2 py-0">{entry.button}</Badge>
        <div className="flex gap-1">
          {entry.reversible ? (
            <Badge variant="outline" className="text-[10px] text-emerald-700 border-emerald-200 px-1.5 py-0">
              Reversible
            </Badge>
          ) : (
            <Badge variant="outline" className="text-[10px] text-red-700 border-red-200 px-1.5 py-0">
              Irreversible
            </Badge>
          )}
          {entry.affectsInventory && (
            <Badge variant="outline" className="text-[10px] text-amber-700 border-amber-200 px-1.5 py-0">
              Affects Stock
            </Badge>
          )}
        </div>
      </div>
      <p className="text-xs text-slate-700">{entry.what}</p>
      <p className="text-xs text-blue-600">
        <ArrowRight className="inline h-3 w-3 mr-1" />
        {entry.continues}
      </p>
    </div>
  )
}

// ── Panel content ─────────────────────────────────────────────────────────────

function PanelContent({ config }: { config: BusinessAssistantConfig }) {
  return (
    <div className="space-y-0 text-sm">
      {/* About + ERP Flow always visible at top */}
      <div className="space-y-4 pb-4">
        <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50 to-slate-50 p-4">
          <SectionLabel>About This Page</SectionLabel>
          <p className="text-xs leading-relaxed text-slate-700">{config.about}</p>
        </div>

        <div>
          <SectionLabel>Business Purpose</SectionLabel>
          <p className="text-xs leading-relaxed text-slate-600">{config.businessPurpose}</p>
        </div>

        <div>
          <SectionLabel>Where This Fits</SectionLabel>
          <FlowDiagram steps={config.erpFlow} />
        </div>

        <div>
          <SectionLabel>What Can I Do Here?</SectionLabel>
          <CheckList items={config.canDo} variant="info" />
        </div>
      </div>

      <Separator className="my-2" />

      {/* Accordion for detailed sections */}
      <Accordion type="multiple" className="w-full">
        {/* Screen Walkthrough */}
        <AccordionItem value="walkthrough">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <BookOpen className="h-3.5 w-3.5 text-blue-500" />
              Screen Walkthrough
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-3">
              {config.screenWalkthrough.map((item, i) => (
                <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-slate-900">{item.section}</p>
                  <p className="mt-1 text-xs text-slate-600">{item.purpose}</p>
                  <p className="mt-1 text-[11px] text-blue-600 font-medium">Impact: {item.impact}</p>
                </div>
              ))}
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Field Guide */}
        {config.fieldGuide.length > 0 && (
          <AccordionItem value="fields">
            <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
              <span className="flex items-center gap-2">
                <HelpCircle className="h-3.5 w-3.5 text-blue-500" />
                Field Guide
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                {config.fieldGuide.map((entry, i) => (
                  <FieldGuideCard key={i} entry={entry} />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Button Guide */}
        {config.buttonGuide.length > 0 && (
          <AccordionItem value="buttons">
            <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
              <span className="flex items-center gap-2">
                <CheckCircle2 className="h-3.5 w-3.5 text-blue-500" />
                Button Guide
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-2">
                {config.buttonGuide.map((entry, i) => (
                  <ButtonGuideCard key={i} entry={entry} />
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Before You Start */}
        <AccordionItem value="before">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Before You Start
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <CheckList items={config.beforeYouStart} variant="success" />
          </AccordionContent>
        </AccordionItem>

        {/* What Happens After Save */}
        <AccordionItem value="after">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <ArrowRight className="h-3.5 w-3.5 text-blue-500" />
              What Happens After Save?
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <FlowDiagram steps={config.afterSave} />
          </AccordionContent>
        </AccordionItem>

        {/* Best Practices */}
        <AccordionItem value="best-practices">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Lightbulb className="h-3.5 w-3.5 text-yellow-500" />
              Best Practices
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <TipList items={config.bestPractices} />
          </AccordionContent>
        </AccordionItem>

        {/* Common Mistakes */}
        <AccordionItem value="mistakes">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500" />
              Common Mistakes
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <WarningList items={config.commonMistakes} />
          </AccordionContent>
        </AccordionItem>

        {/* FAQs */}
        {config.faqs.length > 0 && (
          <AccordionItem value="faqs">
            <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
              <span className="flex items-center gap-2">
                <HelpCircle className="h-3.5 w-3.5 text-slate-500" />
                FAQs
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="space-y-3">
                {config.faqs.map((faq, i) => (
                  <div key={i} className="rounded-lg border border-slate-100 bg-slate-50 p-3">
                    <p className="text-xs font-semibold text-slate-900">Q: {faq.question}</p>
                    <p className="mt-1 text-xs text-slate-600">A: {faq.answer}</p>
                  </div>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}

        {/* Tips & Warnings */}
        <AccordionItem value="tips-warnings">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <Lightbulb className="h-3.5 w-3.5 text-yellow-400" />
              Tips & Warnings
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <div className="space-y-3">
              {config.tips.length > 0 && (
                <div>
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Tips</p>
                  <TipList items={config.tips} />
                </div>
              )}
              {config.warnings.length > 0 && (
                <div>
                  <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Warnings</p>
                  <WarningList items={config.warnings} />
                </div>
              )}
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Success Result */}
        <AccordionItem value="success">
          <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
            <span className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
              Expected Result After Saving
            </span>
          </AccordionTrigger>
          <AccordionContent>
            <CheckList items={config.successResult} variant="success" />
          </AccordionContent>
        </AccordionItem>

        {/* Related Screens */}
        {config.relatedScreens.length > 0 && (
          <AccordionItem value="related">
            <AccordionTrigger className="text-xs font-semibold text-slate-800 hover:no-underline py-3">
              <span className="flex items-center gap-2">
                <ArrowRight className="h-3.5 w-3.5 text-blue-500" />
                Related Screens
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="flex flex-wrap gap-2">
                {config.relatedScreens.map((s, i) => (
                  <a
                    key={i}
                    href={s.href}
                    className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-700 hover:border-blue-300 hover:text-blue-700 transition-colors"
                  >
                    {s.label}
                    <ChevronRight className="h-3 w-3" />
                  </a>
                ))}
              </div>
            </AccordionContent>
          </AccordionItem>
        )}
      </Accordion>
    </div>
  )
}

// ── Main Panel ────────────────────────────────────────────────────────────────

interface BusinessAssistantPanelProps {
  config: BusinessAssistantConfig
  /** If provided, renders a trigger button. If omitted, control open state externally. */
  triggerLabel?: string
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

export function BusinessAssistantPanel({
  config,
  triggerLabel,
  open: controlledOpen,
  onOpenChange,
}: BusinessAssistantPanelProps) {
  const [internalOpen, setInternalOpen] = useState(false)
  const isOpen = controlledOpen !== undefined ? controlledOpen : internalOpen
  const setOpen = onOpenChange ?? setInternalOpen

  return (
    <>
      {/* Floating trigger button (rendered inline, positioned by parent) */}
      {triggerLabel !== undefined && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setOpen(true)}
          className="gap-2 border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 hover:border-blue-300 text-xs font-medium shadow-sm"
        >
          <GraduationCap className="h-3.5 w-3.5" />
          {triggerLabel || "Business Assistant"}
        </Button>
      )}

      <Sheet open={isOpen} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="flex w-full flex-col border-l border-slate-200 p-0 sm:max-w-md"
        >
          {/* Header */}
          <SheetHeader className="border-b border-slate-100 px-5 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 shadow-sm">
                  <GraduationCap className="h-4 w-4 text-white" />
                </div>
                <div>
                  <SheetTitle className="text-sm font-semibold text-slate-900">
                    Business Assistant
                  </SheetTitle>
                  <p className="text-[11px] text-slate-500">{config.pageTitle}</p>
                </div>
              </div>
              <SheetClose asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7 rounded-full">
                  <X className="h-3.5 w-3.5" />
                </Button>
              </SheetClose>
            </div>
          </SheetHeader>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto px-5 py-4">
            <PanelContent config={config} />
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 px-5 py-3">
            <p className="text-[11px] text-slate-400 text-center">
              MedTrack Business Assistant — always based on actual implementation
            </p>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
