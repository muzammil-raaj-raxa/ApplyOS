import { useEffect, useState } from 'react'

type Health = Record<string, boolean>

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [error, setError] = useState(false)

  useEffect(() => {
    fetch('/api/health')
      .then(r => r.json())
      .then(setHealth)
      .catch(() => setError(true))
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-10">
      <h1 className="text-3xl font-bold">ApplyOS</h1>
      <p className="text-slate-400 mb-6">Local-first job application agent</p>
      {error && <p className="text-red-400">Backend unreachable</p>}
      {health && (
        <ul className="space-y-1">
          {Object.entries(health).map(([k, v]) => (
            <li key={k}>{v ? '🟢' : '🔴'} {k}</li>
          ))}
        </ul>
      )}
    </div>
  )
}