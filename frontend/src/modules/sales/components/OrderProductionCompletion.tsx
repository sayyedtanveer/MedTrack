import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { usePermissions } from '@/hooks/usePermissions'
import { extractErrorMessage } from '@/services/api-client'
import { productionCompletion } from '../services/productionCompletion'
import type { SalesOrderLine } from '@/types/sales.types'

interface Props {
  orderId: string
  products: Pick<SalesOrderLine, 'product_id' | 'product_name' | 'product_code'>[]
  onCompleted?: () => void
}

export function OrderProductionCompletion({ orderId, products, onCompleted }: Props) {
  const queryClient = useQueryClient()
  const { hasPermission } = usePermissions()
  const { data, isPending, error } = useQuery({
    queryKey: ['production-completion', orderId],
    queryFn: () => productionCompletion.get(orderId),
    staleTime: 0,
  })
  const completion = useMutation({
    mutationFn: () => productionCompletion.complete(orderId),
    onSuccess: (response) => {
      queryClient.setQueryData(['production-completion', orderId], response)
      void queryClient.invalidateQueries({ queryKey: ['delivery-dispatch-queue'] })
      void queryClient.invalidateQueries({ queryKey: ['work-orders'] })
      onCompleted?.()
    },
  })
  if (isPending) return <p>Checking production…</p>
  if (error) return <p role="alert">{isAxiosError(error) ? extractErrorMessage(error) : error.message}</p>
  const items = data?.items ?? []
  if (items.length === 0) return null
  const ready = items.filter(item => item.status === 'FG_RECEIVED')
  const pending = items.filter(item => !['FG_RECEIVED', 'COMPLETED', 'CLOSED', 'CANCELLED'].includes(item.status))
  return (
    <Card>
      <CardHeader><CardTitle>Production completion</CardTitle></CardHeader>
      <CardContent className="space-y-3">
        <p>{ready.length} ready to complete · {pending.length} awaiting production or QC</p>
        <ul className="text-sm text-muted-foreground space-y-1">
          {items.map(item => {
            const product = products.find(product => product.product_id === item.product_id)
            return <li key={item.id}>{product?.product_name || product?.product_code || item.wo_number} — {item.status === 'FG_RECEIVED' ? 'Ready to complete' : item.status.replace(/_/g, ' ')}</li>
          })}
        </ul>
        {completion.error && <p role="alert" className="text-destructive">{isAxiosError(completion.error) ? extractErrorMessage(completion.error) : completion.error.message}</p>}
        {ready.length > 0 && (
          <Button disabled={completion.isPending || !hasPermission('manufacturing:write')}
            onClick={() => completion.mutate()}>
            {completion.isPending ? 'Completing…' : pending.length > 0 ? 'Complete Ready Products' : 'Complete All Products'}
          </Button>
        )}
        {ready.length === 0 && pending.length === 0 && <p>All production work orders are complete.</p>}
        {!hasPermission('manufacturing:write') && ready.length > 0 && (
          <p className="text-sm text-muted-foreground">Ask a user with manufacturing permission to complete these work orders.</p>
        )}
      </CardContent>
    </Card>
  )
}
