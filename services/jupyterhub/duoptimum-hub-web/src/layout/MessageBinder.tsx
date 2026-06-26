/* Binds antd's context-aware message API and the React Query client to the
 * action layer, so toasts fired from non-component code (table cell renders) are
 * themed correctly and live operations can invalidate the cache after a write. */
import { App } from 'antd'
import { useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { bindMessage, bindModal, bindQueryClient } from '../services/actions'

export function MessageBinder() {
  const { message, modal } = App.useApp()
  const qc = useQueryClient()
  useEffect(() => {
    bindMessage(message)
  }, [message])
  useEffect(() => {
    bindModal(modal)
  }, [modal])
  useEffect(() => {
    bindQueryClient(qc)
  }, [qc])
  return null
}
