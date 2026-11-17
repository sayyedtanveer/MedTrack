import { ArrowDown, ArrowRight, ArrowUpRight, BookOpen, ClipboardList, Layers3, Package, Waypoints } from "lucide-react"
import { Link } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger,
} from "@/components/ui/sheet"

const example = [
  { label: "Material", detail: "Wooden chair seat · Semi-Finished" },
  { label: "Variant", detail: "Standard chair seat, linked to Wooden chair seat" },
  { label: "Active BOM", detail: "1 wooden board per seat · 0% scrap" },
  { label: "Subcontract order", detail: "Send 100 boards · Receive 100 chair seats" },
] as const

const steps = [
  {
    title: "Prepare the output material",
    description: "In Materials, find the item you expect back from the supplier. If it’s missing, create it as Semi-Finished and set its base unit of measure.",
    icon: Package,
    link: { label: "Open Materials", to: "/inventory/materials" },
  },
  {
    title: "Link the product variant",
    description: "In Products, open or create the template and variant. When adding a variant, choose Semi-finished (subcontracting) under Inventory item for this variant and select the item from step 1. When editing, use Finished Good Inventory Item and pick from the Semi-Finished group. Check that the template and variant are active and the stock units match.",
    icon: Layers3,
    link: { label: "Open Products", to: "/products" },
  },
  {
    title: "Set up the BOM",
    description: "Use an active BOM for that variant, or create one. Add the materials you’ll send to the supplier as direct material lines, with quantities per output unit, each material’s base unit, and scrap if needed. Have an authorized user activate the BOM.",
    icon: Waypoints,
    link: { label: "Open BOMs", to: "/bom/list" },
  },
  {
    title: "Create the subcontract order",
    description: "Choose New order. Select the supplier and semi-finished output, confirm the BOM if you’re using one, and enter the quantity and optional due date. Create the draft and open it for approval.",
    icon: ClipboardList,
    link: null,
  },
] as const

export function SubcontractFlowGuide(): JSX.Element {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button type="button" variant="outline" className="w-full sm:w-auto">
          <BookOpen className="mr-2 h-4 w-4" aria-hidden="true" />
          Workflow guide
        </Button>
      </SheetTrigger>
      <SheetContent className="flex w-full flex-col gap-0 p-0 sm:max-w-xl">
        <SheetHeader className="shrink-0 border-b bg-muted/40 px-5 py-6 pr-12 text-left sm:px-7 sm:pr-12">
          <SheetTitle className="text-xl">Semi-finished subcontracting</SheetTitle>
          <SheetDescription>Prepare the item your supplier will make, then create the order.</SheetDescription>
        </SheetHeader>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto px-5 py-5 sm:px-7">
          <section aria-labelledby="subcontract-guide-example" className="rounded-xl border bg-muted/40 p-4">
            <h3 id="subcontract-guide-example" className="text-sm font-semibold">Example: Have a supplier cut wooden chair seats</h3>
            <ol className="mt-3 flex flex-col gap-2 sm:flex-row">
              {example.map(({ label, detail }, index) => (
                <li key={label} className="flex min-w-0 flex-1 flex-col items-center gap-2 sm:flex-row">
                  {index > 0 && (
                    <>
                      <ArrowDown aria-hidden="true" className="h-4 w-4 shrink-0 text-muted-foreground sm:hidden" />
                      <ArrowRight aria-hidden="true" className="hidden h-4 w-4 shrink-0 text-muted-foreground sm:block" />
                    </>
                  )}
                  <div className="w-full min-w-0 flex-1 self-stretch rounded-md border bg-background p-2.5">
                    <p className="text-xs font-semibold text-primary">{label}</p>
                    <p className="mt-1 text-xs leading-relaxed text-foreground">{detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          <ol className="relative space-y-4 before:absolute before:bottom-8 before:left-[1.125rem] before:top-8 before:w-px before:bg-border">
            {steps.map(({ title, description, icon: Icon, link }, index) => (
              <li key={title} className="relative flex items-start gap-3">
                <span aria-hidden="true" className="mt-3 grid h-9 w-9 shrink-0 place-items-center rounded-full border border-border bg-background text-sm font-semibold tabular-nums">
                  {index + 1}
                </span>
                <div className="min-w-0 flex-1 rounded-xl border bg-card px-4 py-3 text-card-foreground">
                  <h3 className="flex items-start gap-2 text-sm font-semibold">
                    <Icon className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
                    {title}
                  </h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
                  {link && (
                    <Link to={link.to} className="mt-1 inline-flex min-h-9 items-center gap-1.5 rounded-sm text-sm font-medium text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
                      {link.label}
                      <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ol>

          <div className="rounded-xl bg-muted px-4 py-3">
            <h3 className="text-sm font-semibold">Manual order</h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              If the order form finds no active BOM for the output, you can go from step 1 to step 4 and issue materials manually after approval.
            </p>
          </div>
          <div>
            <h3 className="text-sm font-semibold">After approval</h3>
            <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
              In the order, use Issue Material when sending stock to the supplier. Use Receive processed output when the semi-finished items come back.
            </p>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
