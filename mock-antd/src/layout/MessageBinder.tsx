/* Binds antd's context-aware message API to the mockAction helper, so toasts
 * fired from non-component code (table cell renders) are themed correctly. */
import { App } from 'antd'
import { useEffect } from 'react'
import { bindMessage } from '../services/actions'

export function MessageBinder() {
  const { message } = App.useApp()
  useEffect(() => {
    bindMessage(message)
  }, [message])
  return null
}
