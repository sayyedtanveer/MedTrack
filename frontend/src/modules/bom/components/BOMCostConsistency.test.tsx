import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { BOMCostBreakdown } from './BOMCostBreakdown'
import { BOMTreeView } from './BOMTreeView'
import { BOMLineForm } from './BOMLineForm'
import type { BOM, BOMCostResponse, BOMTreeNode } from '@/modules/bom/types/bom.types'

const mocks = vi.hoisted(() => ({ cost: vi.fn(), tree: vi.fn() }))
vi.mock('@/services/bom.service', () => ({ bomService: {
  getBOMCost: mocks.cost, getBOMTree: mocks.tree,
  getOperations: vi.fn().mockResolvedValue([]), getWorkstations: vi.fn().mockResolvedValue([]),
  getMaterials: vi.fn().mockResolvedValue({
    items: [
      { id: 'board', name: 'Wooden board', code: 'RM-001', material_type: 'raw', base_unit_id: 'pcs' },
      { id: 'seat', name: 'Wooden chair seat', code: 'SF-001', material_type: 'semi_finished', base_unit_id: 'pcs' },
    ],
  }),
} }))
vi.mock('@/services/material.service', () => ({ materialService: {
  getUnits: vi.fn().mockResolvedValue([
    { id: 'pcs', code: 'PCS', name: 'Pieces', is_active: true },
    { id: 'box', code: 'BOX', name: 'Box', is_active: false },
  ]),
} }))

const bom: BOM = {
  id: 'parent', tenant_id: 'tenant', version: '1', is_active: true, valid_from: null, valid_to: null,
  created_by: null, approved_by: null, template_id: null, variant_id: 'parent-variant',
  created_at: '', updated_at: '', operations_count: 0, operations: [], lines: [],
}
const cost: BOMCostResponse = {
  bom_id: 'parent', material_cost: 312, operation_cost: 0, making_cost: 0, total_cost: 312,
  is_complete: true, missing_costs: [], currency_code: 'INR', currency_symbol: '₹',
}
const tree: BOMTreeNode = {
  id: 'parent', name: 'Parent BOM', type: 'variant', depth: 0, quantity: 1, cost: 312,
  is_complete: true, currency_code: 'INR', currency_symbol: '₹',
  children: [
    { id: 'semi', line_id: 'semi-line', name: 'Child assembly', code: 'SF', type: 'material',
      material_type: 'semi_finished', depth: 1, quantity: 2, unit: 'PCS', cost: 300,
      is_complete: true, cost_basis: 'CHILD_BOM', making_cost: 60, operation_cost: 0,
      children: [
        { id: 'A', name: 'Raw A', type: 'material', depth: 2, quantity: 2, unit: 'PCS', cost: 200, is_complete: true, children: [] },
        { id: 'B', name: 'Raw B', type: 'material', depth: 2, quantity: 2, unit: 'PCS', cost: 20, is_complete: true, children: [] },
        { id: 'C', name: 'Raw C', type: 'material', depth: 2, quantity: 2, unit: 'PCS', cost: 20, is_complete: true, children: [] },
      ] },
    { id: 'extra', line_id: 'extra-line', name: 'Additional raw', type: 'material', depth: 1,
      quantity: 1, unit: 'PCS', cost: 12, is_complete: true, cost_basis: 'STANDARD_COST', children: [] },
  ],
}

function show(element: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={client}>{element}</QueryClientProvider>)
}
beforeEach(() => { mocks.cost.mockResolvedValue(cost); mocks.tree.mockResolvedValue(tree) })
afterEach(() => { cleanup(); vi.clearAllMocks() })

it('requires an explicit active unit even when the component has a stock unit', async () => {
  HTMLElement.prototype.scrollIntoView ??= vi.fn()
  const onAdd = vi.fn()
  show(<BOMLineForm onAdd={onAdd} onCancel={vi.fn()} />)
  fireEvent.change(screen.getByPlaceholderText('Search raw material by name or code...'), { target: { value: 'board' } })
  fireEvent.click(await screen.findByRole('button', { name: /Wooden board/ }))

  const addLine = screen.getByRole('button', { name: 'Add Line' })
  expect(addLine).toBeDisabled()
  expect(await screen.findByText('Stock unit for this component: PCS')).toBeVisible()
  const unit = screen.getByRole('combobox', { name: 'Unit of measure (required)' })
  await waitFor(() => expect(unit).toBeEnabled())
  expect(unit).toHaveTextContent('Select a unit')
  fireEvent.keyDown(unit, { key: 'Enter' })
  expect(screen.getAllByRole('option')).toHaveLength(1)
  fireEvent.click(screen.getByRole('option', { name: 'PCS — Pieces' }))
  fireEvent.click(addLine)
  expect(onAdd).toHaveBeenCalledWith({ material_id: 'board', unit_id: 'pcs', quantity: 1, scrap_percentage: 0 })

  fireEvent.click(screen.getByRole('radio', { name: 'Semi-finished item' }))
  fireEvent.change(screen.getByRole('textbox', { name: 'Search semi-finished items' }), { target: { value: 'wooden' } })
  fireEvent.click(await screen.findByRole('button', { name: /Wooden chair seat/ }))
  expect(addLine).toBeDisabled()
  fireEvent.keyDown(unit, { key: 'Enter' })
  fireEvent.click(await screen.findByRole('option', { name: 'PCS — Pieces' }))
  fireEvent.click(addLine)
  expect(onAdd).toHaveBeenLastCalledWith({ material_id: 'seat', unit_id: 'pcs', quantity: 1, scrap_percentage: 0 })
})

describe('BOM cost and explanatory tree', () => {
  it('shows one component contribution per branch, reconciling 300 + 12 = 312', async () => {
    show(<BOMCostBreakdown bom={bom} />)
    await screen.findByText('Child assembly')
    const table = screen.getByRole('table')
    expect(within(table).getAllByRole('row')).toHaveLength(3)
    expect(within(table).getByText('₹ 300.00')).toBeInTheDocument()
    expect(within(table).getByText('₹ 12.00')).toBeInTheDocument()
    expect(within(table).queryByText('Raw A')).not.toBeInTheDocument()
    expect(screen.getByText(/Child BOM total; includes/)).toBeInTheDocument()
    expect(screen.getAllByText('₹ 312.00').length).toBeGreaterThan(0)
  })

  it('uses tenant currency and labels expanded details as already included', async () => {
    show(<BOMTreeView bomId="parent" />)
    fireEvent.click(await screen.findByText('Child assembly'))
    expect(screen.getByText('Raw A')).toBeInTheDocument()
    expect(screen.getByText('Child BOM contribution').nextElementSibling).toHaveTextContent('₹ 300.00')
    expect(screen.getByText('₹ 200.00')).toHaveAttribute('title', 'Included in parent branch total; explanatory detail')
    expect(screen.getByText('Outside Processing Cost (child BOM)').nextElementSibling).toHaveTextContent('₹ 60.00')
    expect(screen.queryByText('$300.00')).not.toBeInTheDocument()
  })

  it('shows the parent total and its own outside processing even when the tree is collapsed', async () => {
    mocks.tree.mockResolvedValue({
      ...tree, cost: 1252, making_cost: 40,
      children: [{ ...tree.children[0], cost: 1200, making_cost: 0 }, tree.children[1]],
    })
    show(<BOMTreeView bomId="parent" />)
    const total = await screen.findByText('Total Standard Cost')
    const processing = screen.getByText('Outside Processing Cost (this BOM)')
    expect(total.nextElementSibling).toHaveTextContent('₹ 1252.00')
    expect(processing.nextElementSibling).toHaveTextContent('₹ 40.00')
    expect(screen.queryByText('Outside Processing Cost (child BOM)')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('Child assembly'))
    expect(screen.queryByText('Outside Processing Cost (child BOM)')).not.toBeInTheDocument()
    expect(screen.queryByText('Operations (child BOM)')).not.toBeInTheDocument()
    expect(screen.getByText('Child BOM contribution').nextElementSibling).toHaveTextContent('₹ 1200.00')
    fireEvent.click(screen.getByTitle('Collapse all nodes to root level'))
    expect(total.nextElementSibling).toHaveTextContent('₹ 1252.00')
    expect(mocks.tree).toHaveBeenCalledTimes(1)
    expect(mocks.tree).toHaveBeenCalledWith('parent', { max_depth: 20 })
  })

  it('shows a child resolution failure as incomplete, never a valid zero total', async () => {
    mocks.cost.mockResolvedValue({ ...cost, total_cost: 0, material_cost: 12, is_complete: false,
      missing_costs: [{ component_type: 'bom', component_id: 'child', name: 'Child assembly',
        reason: 'UOM_INCOMPATIBLE', message: 'Child output UOM differs from component UOM' }] })
    mocks.tree.mockResolvedValue({ ...tree, is_complete: false, cost: null, children: [
      { ...tree.children[0], is_complete: false, cost: null, message: 'Child output UOM differs from component UOM' },
      tree.children[1],
    ] })
    show(<BOMCostBreakdown bom={bom} />)
    expect(await screen.findByText('Incomplete Cost — total cannot be calculated')).toBeInTheDocument()
    expect(screen.getAllByText('Child output UOM differs from component UOM').length).toBeGreaterThan(0)
    const table = screen.getByRole('table')
    expect(within(table).getByText('Incomplete')).toBeInTheDocument()
    expect(within(table).queryByText('₹ 0.00')).not.toBeInTheDocument()
  })
})
