import type { JobFilters as Filters } from '../../lib/types'
import { SearchIcon } from '../ui/icons'
import { Segmented } from '../ui/Segmented'
import { Switch } from '../ui/Switch'

interface Props {
  filters: Filters
  query: string
  onQuery: (value: string) => void
  onChange: (patch: Partial<Filters>) => void
  searchRef?: React.RefObject<HTMLInputElement | null>
}

export function JobFilters({ filters, query, onQuery, onChange, searchRef }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <label className="relative block flex-1">
          <span className="sr-only">Search jobs</span>
          <SearchIcon className="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-fog" />
          <input
            ref={searchRef}
            value={query}
            onChange={(event) => onQuery(event.target.value)}
            placeholder="Search by title or company"
            className="h-11 w-full rounded-full bg-white/[0.045] pr-5 pl-12 text-pearl ring-1 ring-white/[0.08] transition placeholder:text-fog hover:ring-white/20 focus:bg-white/[0.07] focus:ring-2 focus:ring-mint/70 focus:outline-none"
          />
        </label>
        <Segmented
          id="sort"
          label="Sort by"
          value={filters.sort}
          onChange={(sort) => onChange({ sort })}
          options={[
            { value: 'best', label: 'Best fit' },
            { value: 'new', label: 'Newest' },
          ]}
        />
      </div>
      <div className="-mx-[var(--gutter)] flex items-center gap-x-5 gap-y-3 overflow-x-auto px-[var(--gutter)] pb-1 md:mx-0 md:flex-wrap md:overflow-visible md:px-0">
        <Segmented
          id="status"
          label="Show"
          value={filters.status}
          onChange={(status) => onChange({ status })}
          options={[
            { value: 'active', label: 'Active' },
            { value: 'saved', label: 'Saved' },
            { value: 'rejected', label: 'Rejected' },
            { value: 'all', label: 'All' },
          ]}
        />
        <Segmented
          id="fit"
          label="Fit"
          value={filters.fit}
          onChange={(fit) => onChange({ fit })}
          options={[
            { value: 'any', label: 'Any fit' },
            { value: 'unscored', label: 'Not scored' },
            { value: '70', label: '70+' },
            { value: '80', label: '80+' },
            { value: '90', label: '90+' },
          ]}
        />
        <Segmented
          id="where"
          label="Where"
          value={filters.where}
          onChange={(where) => onChange({ where })}
          options={[
            { value: 'any', label: 'Anywhere' },
            { value: 'remote', label: 'Remote' },
            { value: 'hybrid', label: 'Hybrid' },
            { value: 'onsite', label: 'Onsite' },
          ]}
        />
        <Switch checked={filters.all} onChange={(all) => onChange({ all })} label="Include filtered out" />
      </div>
    </div>
  )
}
