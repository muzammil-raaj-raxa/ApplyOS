import { createContext, useContext } from 'react'

export interface ToastInput {
  message: string
  tone?: 'default' | 'error'
  action?: { label: string; onClick: () => void }
}

export const ToastContext = createContext<(toast: ToastInput) => void>(() => {})

export const useToast = () => useContext(ToastContext)
