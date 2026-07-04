import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, X } from 'lucide-react'
import { useWebSocketNotifications, WebSocketNotification } from '@/hooks/useWebSocketNotifications'
import { cn } from '@/lib/utils'

export const RealtimeBell: React.FC = () => {
  const navigate = useNavigate()
  const [isOpen, setIsOpen] = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)
  const [hasShaken, setHasShaken] = useState(false)
  const { notifications, isConnected } = useWebSocketNotifications()

  useEffect(() => {
    setUnreadCount(notifications.length)
  }, [notifications])

  useEffect(() => {
    if (notifications.length > 0) {
      setHasShaken(true)
      setTimeout(() => setHasShaken(false), 600)
    }
  }, [notifications.length])

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('keydown', handleEscape)
      return () => document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      if (!target.closest('[data-notification-bell]')) {
        setIsOpen(false)
      }
    }
    if (isOpen) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [isOpen])

  const getNotificationColor = (type: string) => {
    switch (type) {
      case 'ORDER_STATUS_CHANGED':
      case 'SALES_ORDER_PENDING_APPROVAL':
      case 'CLIENT_ORDER_PENDING_APPROVAL':
      case 'sales_approved':
      case 'payment_received':
      case 'promise_date_at_risk':
        return 'border-l-blue-500 bg-blue-50'
      case 'LOW_STOCK':
      case 'material_shortage':
        return 'border-l-orange-500 bg-orange-50'
      case 'WORK_ORDER_RELEASED':
      case 'WORK_ORDER_STARTED':
      case 'WORK_ORDER_COMPLETED':
      case 'WORK_ORDER_ACTION_REQUIRED':
      case 'PRODUCTION_ACTION_REQUIRED':
      case 'wo_released':
      case 'material_issued':
      case 'start_production_action':
      case 'production_scrap_failed':
        return 'border-l-purple-500 bg-purple-50'
      case 'SUPPLIER_PO_ACTION_REQUIRED':
      case 'requisition_rejected':
      case 'incoming_qc_failed':
        return 'border-l-cyan-500 bg-cyan-50'
      case 'INVOICE_OVERDUE':
      case 'invoice_creation_failed':
        return 'border-l-red-500 bg-red-50'
      case 'QUALITY_INSPECTION_FAILED':
      case 'qc_failed':
      case 'qc_escalation':
        return 'border-l-red-600 bg-red-50'
      case 'fg_received':
      case 'qc_approved':
      case 'receive_fg_action':
        return 'border-l-green-500 bg-green-50'
      case 'dispatch_completed':
      case 'ready_for_dispatch_action':
      case 'delivery_cancelled':
        return 'border-l-teal-500 bg-teal-50'
      case 'machine_breakdown':
        return 'border-l-rose-500 bg-rose-50'
      case 'issue_materials_action':
        return 'border-l-indigo-500 bg-indigo-50'
      default:
        return 'border-l-gray-500 bg-gray-50'
    }
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'ORDER_STATUS_CHANGED':
      case 'SALES_ORDER_PENDING_APPROVAL':
      case 'CLIENT_ORDER_PENDING_APPROVAL':
      case 'sales_approved':
      case 'payment_received':
      case 'promise_date_at_risk':
        return 'O'
      case 'LOW_STOCK':
      case 'material_shortage':
        return '!'
      case 'WORK_ORDER_RELEASED':
      case 'WORK_ORDER_STARTED':
      case 'WORK_ORDER_COMPLETED':
      case 'WORK_ORDER_ACTION_REQUIRED':
      case 'PRODUCTION_ACTION_REQUIRED':
      case 'wo_released':
      case 'material_issued':
      case 'start_production_action':
      case 'production_scrap_failed':
        return 'W'
      case 'SUPPLIER_PO_ACTION_REQUIRED':
      case 'requisition_rejected':
      case 'incoming_qc_failed':
        return 'P'
      case 'INVOICE_OVERDUE':
      case 'invoice_creation_failed':
        return '$'
      case 'QUALITY_INSPECTION_FAILED':
      case 'qc_failed':
      case 'qc_escalation':
        return 'X'
      case 'fg_received':
      case 'qc_approved':
      case 'receive_fg_action':
        return '✓'
      case 'dispatch_completed':
      case 'ready_for_dispatch_action':
      case 'delivery_cancelled':
        return 'D'
      case 'machine_breakdown':
        return '⚠'
      case 'issue_materials_action':
        return 'M'
      default:
        return 'N'
    }
  }

  const formatTime = (isoString: string) => {
    const date = new Date(isoString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMinutes = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMinutes < 1) return 'Just now'
    if (diffMinutes < 60) return `${diffMinutes}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`

    return date.toLocaleDateString()
  }

  const openNotification = (notification: WebSocketNotification) => {
    // Priority 1: Use deep_link if available (new notification format)
    const deepLink = notification.data?.deep_link || (notification as any).deep_link
    if (deepLink && typeof deepLink === 'string') {
      navigate(deepLink)
      setIsOpen(false)
      return
    }

    // Priority 2: Fall back to reference_type/reference_id (legacy format)
    const referenceType = notification.reference_type || notification.data?.reference_type
    const referenceId = notification.reference_id || notification.data?.reference_id

    if (referenceType === 'sales_order' && referenceId) {
      navigate(`/sales/orders/${referenceId}`)
      setIsOpen(false)
      return
    }

    if (referenceType === 'work_order' && referenceId) {
      navigate(`/work-orders/${referenceId}`)
      setIsOpen(false)
      return
    }

    if (referenceType === 'purchase_order' && referenceId) {
      navigate(`/procurement/purchase-orders/${referenceId}`)
      setIsOpen(false)
      return
    }

    if (referenceType === 'delivery' && referenceId) {
      navigate(`/delivery/${referenceId}`)
      setIsOpen(false)
      return
    }

    if (referenceType === 'invoice' && referenceId) {
      navigate(`/finance/invoices/${referenceId}`)
      setIsOpen(false)
      return
    }

    // If no navigation target, keep the panel open
  }

  return (
    <div className="relative" data-notification-bell>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'relative p-2 text-gray-600 hover:text-gray-900 transition-colors',
          hasShaken && 'animate-bounce',
          isConnected ? 'hover:bg-gray-100 rounded-full' : 'opacity-60'
        )}
        aria-label="Notifications"
        title={isConnected ? 'Connected' : 'Disconnected'}
      >
        <Bell className="h-5 w-5" />
        <div
          className={cn(
            'absolute top-1 right-1 h-2 w-2 rounded-full animate-pulse',
            isConnected ? 'bg-green-500' : 'bg-gray-400'
          )}
        />
        {unreadCount > 0 && (
          <span className="absolute top-0 right-0 inline-flex min-w-[20px] -translate-y-1/2 translate-x-1/2 items-center justify-center rounded-full bg-red-600 px-2 py-1 text-xs font-bold leading-none text-white">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 z-50 mt-2 flex max-h-96 w-96 flex-col overflow-hidden rounded-lg border border-gray-200 bg-white shadow-lg animate-in fade-in slide-in-from-top-2 duration-200">
          <div className="flex items-center justify-between border-b border-gray-200 bg-gray-50 px-4 py-3">
            <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <span className="inline-flex items-center rounded-full bg-red-100 px-2 py-1 text-xs font-medium text-red-700">
                  {unreadCount} new
                </span>
              )}
              <button
                onClick={() => setIsOpen(false)}
                className="rounded p-1 transition-colors hover:bg-gray-200 hover:text-gray-600"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Bell className="mb-2 h-8 w-8 text-gray-300" />
                <p className="text-sm text-gray-500">No notifications yet</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {notifications.slice(0, 10).map((notification: WebSocketNotification) => (
                  <div
                    key={notification.id}
                    className={cn(
                      'cursor-pointer border-l-4 px-4 py-3 transition-colors hover:bg-gray-50',
                      getNotificationColor(notification.type)
                    )}
                    onClick={() => openNotification(notification)}
                  >
                    <div className="flex items-start gap-3">
                      <span className="mt-1 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-white text-xs font-semibold text-gray-700">
                        {getNotificationIcon(notification.type)}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="line-clamp-2 text-sm font-semibold text-gray-900">
                          {notification.title}
                        </p>
                        <p className="mt-1 line-clamp-2 text-xs text-gray-600">
                          {notification.message}
                        </p>
                        <p className="mt-2 text-xs text-gray-500">
                          {formatTime(notification.timestamp)}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {notifications.length > 0 && (
            <div className="border-t border-gray-200 bg-gray-50 px-4 py-3">
              <button
                onClick={() => setIsOpen(false)}
                className="text-xs font-medium text-blue-600 transition-colors hover:text-blue-700"
              >
                Close notifications
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default RealtimeBell
