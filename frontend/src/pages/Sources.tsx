import { AnimatePresence, motion } from 'motion/react'
import { useState } from 'react'
import { TagEditor } from '../components/sources/TagEditor'
import { Button } from '../components/ui/Button'
import { Bar } from '../components/ui/Skeleton'
import { ErrorState } from '../components/ui/StateBlock'
import { describeError } from '../lib/errors'
import { useToast } from '../components/ui/toast-context'
import { useActions } from '../hooks/actions'
import { useSaveSearchProfile, useSearchProfile } from '../hooks/queries'
import { useElapsed } from '../hooks/useElapsed'
import { DURATION, EASE_OUT } from '../lib/motion'
import type { SearchProfile } from '../lib/types'

const SLUG = /^[A-Za-z0-9_.-]+$/
const validateSlug = (value: string) => (SLUG.test(value) ? null : 'Use only letters, numbers, dots, dashes and underscores. Copy it from the job link.')

const BOARDS = [
  { key: 'greenhouse', name: 'Greenhouse', example: 'boards.greenhouse.io/stripe', slug: 'stripe' },
  { key: 'lever', name: 'Lever', example: 'jobs.lever.co/spotify', slug: 'spotify' },
  { key: 'ashby', name: 'Ashby', example: 'jobs.ashbyhq.com/ramp', slug: 'ramp' },
]

export function SourcesPage() {
  const { data, error, refetch, isPending } = useSearchProfile()
  const save = useSaveSearchProfile()
  const toast = useToast()
  const { find, finding } = useActions()
  const elapsed = useElapsed(finding)
  const [draft, setDraft] = useState<SearchProfile | null>(null)

  const profile = draft ?? data
  const dirty = draft !== null && JSON.stringify(draft) !== JSON.stringify(data)

  const update = (patch: Partial<SearchProfile>) => profile && setDraft({ ...profile, ...patch })
  const updateCompanies = (board: string, slugs: string[]) => profile && update({ companies: { ...profile.companies, [board]: slugs } })

  const onSave = () => {
    if (!draft) return
    save.mutate(draft, {
      onSuccess: () => {
        setDraft(null)
        toast({ message: 'Sources saved.' })
      },
    })
  }

  const totalCompanies = profile ? Object.values(profile.companies).reduce((n, list) => n + list.length, 0) : 0

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <div className="max-w-2xl">
          <h1 className="text-display">Sources</h1>
          <p className="mt-5 text-lead text-mist">Where ApplyOS looks for jobs, and what it keeps. Changes apply the next time you find jobs.</p>
        </div>
        <Button variant="primary" loading={finding} disabled={dirty} onClick={() => void find()}>
          {finding ? `Looking… ${elapsed}s` : 'Find new jobs'}
        </Button>
      </div>
      {dirty && <p className="mt-3 text-right text-label text-apricot">Save your changes first.</p>}

      {isPending && (
        <div className="mt-16 space-y-10" role="status" aria-label="Loading sources">
          <Bar className="h-28 w-full" />
          <Bar className="h-28 w-full" />
          <Bar className="h-28 w-full" />
        </div>
      )}
      {error && !data && <ErrorState error={error} onRetry={() => void refetch()} />}

      {profile && (
        <div className="mt-16 space-y-16 pb-24">
          <section className="grid gap-x-16 gap-y-10 lg:grid-cols-2">
            <TagEditor
              label="Roles you want"
              hint="Job titles you would take."
              values={profile.target_roles}
              onChange={(target_roles) => update({ target_roles })}
              placeholder="For example, iOS Engineer"
            />
            <TagEditor
              label="Skip titles containing"
              hint="Anything with these words in the title is filtered out."
              values={profile.exclude_keywords}
              onChange={(exclude_keywords) => update({ exclude_keywords })}
              placeholder="For example, Principal"
            />
          </section>

          <section>
            <div className="max-w-2xl">
              <h2 className="text-section">Companies</h2>
              <p className="mt-3 text-mist">
                {totalCompanies} {totalCompanies === 1 ? 'company' : 'companies'} across three job boards. Each company's board name is in the link of any of its job postings.
                A name that does not exist shows up as an error when you find jobs.
              </p>
            </div>
            <div className="mt-8 grid gap-10 lg:grid-cols-3">
              {BOARDS.map((board) => (
                <TagEditor
                  key={board.key}
                  label={board.name}
                  hint={`From ${board.example}, add ${board.slug}.`}
                  values={profile.companies[board.key] ?? []}
                  onChange={(slugs) => updateCompanies(board.key, slugs)}
                  placeholder={board.slug}
                  validate={validateSlug}
                />
              ))}
            </div>
          </section>

          <section className="grid gap-x-16 gap-y-10 lg:grid-cols-2">
            <TagEditor
              label="Employment types"
              hint="Postings with a different type are filtered out."
              values={profile.employment_types}
              onChange={(employment_types) => update({ employment_types })}
              placeholder="For example, Full-time"
            />
            <TagEditor
              label="Places you would work"
              hint="Kept for scoring. Remote, a country, or a city."
              values={profile.locations}
              onChange={(locations) => update({ locations })}
              placeholder="For example, Remote"
            />
          </section>

          <section className="max-w-2xl">
            <h2 className="text-section">What counts as a strong fit</h2>
            <p className="mt-3 text-mist">Jobs scoring at least this much show up as strong fits on Today.</p>
            <div className="mt-6 flex items-center gap-8">
              <span className="tnum w-24 text-title">{profile.minimum_score}</span>
              <input
                type="range"
                min={50}
                max={100}
                step={1}
                value={profile.minimum_score}
                aria-label="Minimum score for a strong fit"
                onChange={(event) => update({ minimum_score: Number(event.target.value) })}
                className="range"
                style={{ ['--fill' as string]: `${((profile.minimum_score - 50) / 50) * 100}%` }}
              />
            </div>
          </section>
        </div>
      )}

      <AnimatePresence>
        {dirty && (
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0, transition: { duration: DURATION.base, ease: EASE_OUT } }}
            exit={{ opacity: 0, y: 16, transition: { duration: DURATION.quick } }}
            className="fixed inset-x-0 bottom-[calc(6.25rem+env(safe-area-inset-bottom))] z-30 flex justify-center px-4"
          >
            <div className="glass flex w-full max-w-xl flex-wrap items-center gap-x-5 gap-y-3 rounded-3xl py-3 pr-3 pl-6">
              <p className="flex-1 text-pearl">{save.error ? <span className="text-coral">{describeError(save.error).body}</span> : 'You have unsaved changes.'}</p>
              <Button variant="ghost" onClick={() => { setDraft(null); save.reset() }}>
                Discard
              </Button>
              <Button variant="primary" loading={save.isPending} onClick={onSave}>
                Save changes
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
