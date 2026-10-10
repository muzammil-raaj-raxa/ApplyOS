import type { SVGProps } from 'react'

// A small hand-drawn set on a 24px grid. Round caps, 1.7 stroke, no fills unless meant.
function Icon({ children, ...props }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 24 24"
      width="20"
      height="20"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      {...props}
    >
      {children}
    </svg>
  )
}

type P = SVGProps<SVGSVGElement>

export const TodayIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="8.2" opacity=".45" />
    <path d="M12 3.8a8.2 8.2 0 0 1 8.2 8.2" />
    <circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none" />
  </Icon>
)
export const JobsIcon = (p: P) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h11M4 17h7" />
  </Icon>
)
export const SourcesIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="9" cy="12" r="5.2" />
    <circle cx="15.5" cy="12" r="5.2" opacity=".55" />
  </Icon>
)
export const SearchIcon = (p: P) => (
  <Icon {...p}>
    <circle cx="10.8" cy="10.8" r="6" />
    <path d="m15.4 15.4 4.4 4.4" />
  </Icon>
)
export const BookmarkIcon = ({ filled, ...p }: P & { filled?: boolean }) => (
  <Icon {...p}>
    <path d="M7 4.5h10a1 1 0 0 1 1 1V20l-6-4.2L6 20V5.5a1 1 0 0 1 1-1Z" fill={filled ? 'currentColor' : 'none'} />
  </Icon>
)
export const CloseIcon = (p: P) => (
  <Icon {...p}>
    <path d="m6 6 12 12M18 6 6 18" />
  </Icon>
)
export const ExternalIcon = (p: P) => (
  <Icon {...p}>
    <path d="M10 5H6.5A1.5 1.5 0 0 0 5 6.5v11A1.5 1.5 0 0 0 6.5 19h11a1.5 1.5 0 0 0 1.5-1.5V14M13.5 5H19v5.5M19 5l-8 8" />
  </Icon>
)
export const CheckIcon = (p: P) => (
  <Icon {...p}>
    <path d="m5 12.5 4.5 4.5L19 7.5" />
  </Icon>
)
export const PlusIcon = (p: P) => (
  <Icon {...p}>
    <path d="M12 5v14M5 12h14" />
  </Icon>
)
export const UndoIcon = (p: P) => (
  <Icon {...p}>
    <path d="M9 7 4.5 11.5 9 16" />
    <path d="M5 11.5h9.5a5 5 0 0 1 0 10H12" transform="translate(0 -4)" />
  </Icon>
)
export const ChevronIcon = (p: P) => (
  <Icon {...p}>
    <path d="m9 6 6 6-6 6" />
  </Icon>
)
