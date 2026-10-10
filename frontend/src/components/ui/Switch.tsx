interface SwitchProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label: string
}

export function Switch({ checked, onChange, label }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2.5 text-label text-mist transition-colors hover:text-pearl"
    >
      <span className={`relative h-5 w-9 rounded-full transition-colors duration-200 ${checked ? 'bg-mint' : 'bg-white/20'}`} aria-hidden="true">
        <span
          className={`absolute top-0.5 left-0.5 size-4 rounded-full shadow transition-transform duration-200 ease-out-expo ${checked ? 'bg-spruce-900' : 'bg-pearl'}`}
          style={{ transform: `translateX(${checked ? 16 : 0}px)` }}
        />
      </span>
      {label}
    </button>
  )
}
