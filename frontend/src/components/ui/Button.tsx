import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'md' | 'sm' | 'icon'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-pearl text-spruce-900 hover:bg-white hover:shadow-[0_10px_34px_-10px_rgb(124_242_184/0.65)] disabled:bg-pearl/40 disabled:text-spruce-900/60',
  secondary:
    'border border-white/15 bg-white/[0.04] text-pearl hover:border-white/30 hover:bg-white/[0.09] disabled:text-mist/60 disabled:hover:bg-white/[0.04] disabled:hover:border-white/15',
  ghost: 'text-mist hover:bg-white/[0.07] hover:text-pearl disabled:text-fog disabled:hover:bg-transparent',
  danger: 'text-coral hover:bg-coral/10 disabled:text-coral/40 disabled:hover:bg-transparent',
}

const SIZES: Record<Size, string> = {
  md: 'h-11 gap-2.5 rounded-control px-5 text-[0.9375rem] font-semibold',
  sm: 'h-9 gap-2 rounded-control px-3.5 text-label',
  icon: 'h-9 w-9 justify-center rounded-control',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  loading?: boolean
  icon?: ReactNode
}

export function Button({ variant = 'secondary', size = 'md', loading = false, icon, className = '', children, disabled, ...rest }: ButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={`inline-flex shrink-0 select-none items-center whitespace-nowrap transition duration-150 ease-out-expo active:scale-[0.98] ${VARIANTS[variant]} ${SIZES[size]} ${className}`}
      {...rest}
    >
      {loading ? <Spinner size={size === 'md' ? 18 : 16} /> : icon}
      {children}
    </button>
  )
}
