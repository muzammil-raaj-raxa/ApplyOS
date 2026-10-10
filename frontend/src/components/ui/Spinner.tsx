/** A short arc turning around a faint ring: the product's "working" mark. */
export function Spinner({ size = 16 }: { size?: number }) {
  return (
    <svg className="animate-orbit" width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeOpacity=".22" strokeWidth="2.6" />
      <path d="M12 3a9 9 0 0 1 9 9" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" />
    </svg>
  )
}
