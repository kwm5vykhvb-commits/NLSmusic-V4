import { useEffect, useState } from 'react'
import { downloadTrack, fetchDownloads } from '../lib/api'

export default function DownloadsPage() {
  const [items, setItems] = useState([])

  useEffect(() => {
    ;(async () => {
      try {
        const data = await fetchDownloads()
        setItems(data.items || [])
      } catch {
        setItems([])
      }
    })()
  }, [])

  return (
    <div className="pb-24">
      <h1 className="mb-4 text-2xl font-semibold text-white">My Downloads</h1>
      <div className="space-y-2">
        {items.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => downloadTrack(item.id)}
            className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 p-3 text-left"
          >
            <div>
              <p className="text-sm text-white">{item.title}</p>
              <p className="text-xs text-zinc-400">{item.artist}</p>
            </div>
            <span className="text-xs text-zinc-500">{item.source}</span>
          </button>
        ))}
      </div>
    </div>
  )
}
