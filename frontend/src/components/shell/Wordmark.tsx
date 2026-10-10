export function Wordmark() {
  return (
    <div className="flex items-center gap-2.5 select-none">
      <svg width="26" height="26" viewBox="0 0 64 64" aria-hidden="true">
        <circle cx="32" cy="32" r="18" fill="none" stroke="rgb(255 255 255 / 0.16)" strokeWidth="7" />
        <path d="M32 14 A18 18 0 1 1 15.3 38.6" fill="none" stroke="var(--color-mint)" strokeWidth="7" strokeLinecap="round" />
      </svg>
      <span className="text-[1.0625rem] font-[640] tracking-tight text-pearl">ApplyOS</span>
    </div>
  )
}
