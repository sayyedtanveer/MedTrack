import { useEffect, useCallback, useRef, useState } from 'react'
import { useAuthStore } from '@/app/store/authStore'

export interface WebSocketNotification {
  id: string
  type: string
  title: string
  message: string
  reference_type?: string | null
  reference_id?: string | null
  data?: Record<string, any>
  timestamp: string
}

interface UseWebSocketNotificationsProps {
  onNotification?: (notification: WebSocketNotification) => void
  autoReconnect?: boolean
  reconnectInterval?: number
  maxReconnectAttempts?: number
}

/**
 * Custom hook for WebSocket real-time notifications.
 *
 * Usage:
 * ```
 * const { isConnected, notifications, error } = useWebSocketNotifications({
 *   onNotification: (notif) => showToast(notif),
 * })
 * ```
 */
export const useWebSocketNotifications = ({
  onNotification,
  autoReconnect = true,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: UseWebSocketNotificationsProps = {}) => {
  const { token, isAuthenticated } = useAuthStore()
  const [isConnected, setIsConnected] = useState(false)
  const [notifications, setNotifications] = useState<WebSocketNotification[]>([])
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const heartbeatIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Get API base URL (supports both HTTP and WebSocket protocols)
  const getWebSocketUrl = useCallback(() => {
    const apiBase = import.meta.env.VITE_PROD_BACKEND_URL || import.meta.env.VITE_API_URL || '/api/v1'
    const absoluteBase = apiBase.startsWith('http')
      ? apiBase
      : `${window.location.origin}${apiBase.startsWith('/') ? apiBase : `/${apiBase}`}`
    const url = new URL(absoluteBase)
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
    url.pathname = `${url.pathname.replace(/\/$/, '')}/ws/notifications`
    url.searchParams.set('token', token || '')
    return url.toString()
  }, [token])

  // Connect to WebSocket
  const connect = useCallback(() => {
    if (!isAuthenticated || !token) {
      setError('Not authenticated')
      return
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return // Already connected
    }

    try {
      const wsUrl = getWebSocketUrl()
      const ws = new WebSocket(wsUrl)

      ws.onopen = () => {
        console.log('[WebSocket] Connected to notifications')
        setIsConnected(true)
        setError(null)
        reconnectCountRef.current = 0

        // Send periodic heartbeat
        heartbeatIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping')
          }
        }, 30000) // Heartbeat every 30 seconds
      }

      ws.onmessage = (event) => {
        try {
          if (event.data === 'pong') {
            return
          }

          const data = JSON.parse(event.data)

          if (data.type === 'pong') {
            // Ignore pong responses
            return
          }

          if (data.type === 'notification' && data.payload) {
            const notification: WebSocketNotification = data.payload

            // Add to notifications list
            setNotifications((prev) => [notification, ...prev])

            // Trigger callback if provided
            if (onNotification) {
              onNotification(notification)
            }

            console.log('[WebSocket] Received notification:', notification.title)
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err)
        }
      }

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event)
        setError('WebSocket error')
        setIsConnected(false)
      }

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected')
        setIsConnected(false)

        // Clear heartbeat
        if (heartbeatIntervalRef.current) {
          clearInterval(heartbeatIntervalRef.current)
        }

        // Attempt reconnection
        if (autoReconnect && reconnectCountRef.current < maxReconnectAttempts) {
          reconnectCountRef.current += 1
          console.log(
            `[WebSocket] Reconnecting... (attempt ${reconnectCountRef.current}/${maxReconnectAttempts})`
          )

          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, reconnectInterval)
        } else if (reconnectCountRef.current >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached')
        }
      }

      wsRef.current = ws
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : String(err)
      setError(errorMsg)
      setIsConnected(false)
    }
  }, [isAuthenticated, token, getWebSocketUrl, autoReconnect, reconnectInterval, maxReconnectAttempts, onNotification])

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    if (heartbeatIntervalRef.current) {
      clearInterval(heartbeatIntervalRef.current)
    }

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }

    setIsConnected(false)
  }, [])

  // Clear notifications
  const clearNotifications = useCallback(() => {
    setNotifications([])
  }, [])

  // Auto-connect on mount and when auth changes
  useEffect(() => {
    if (isAuthenticated && token) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [isAuthenticated, token, connect, disconnect])

  return {
    isConnected,
    notifications,
    error,
    connect,
    disconnect,
    clearNotifications,
  }
}

export default useWebSocketNotifications
