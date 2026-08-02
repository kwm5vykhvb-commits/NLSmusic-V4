import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useMemo, useState } from 'react'
import SkeletonCard from '../components/SkeletonCard'
import TrackCard from '../components/TrackCard'
import { downloadTrack, fetchSuggestions, searchTracks } from '../lib/api'

const tabs = ['all', 'songs', 'artists']

export default function SearchPage({ query, setQuery, onPlay, currentTrack, playing }) {
  const [tab, setTab] = useState('all')
  const [loading, setLoading] = useState(false)
  const [results, setResults] = useState({ cloud: [], archives: [] })
  const [suggestions, setSuggestions] = useState({ songs: [], artists: [] })
  const [page, setPage] = useState(1)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!query.trim()) {
      setSuggestions({ songs: [], artists: [] })
      return
    }

    const timeout = setTimeout(async () => {
      try {
        setSuggestions(await fetchSuggestions(query))
      } catch {
        setSuggestions({ songs: [], artists: [] })
      }
    }, 300)

    return () => clearTimeout(timeout)
  }, [query])

  useEffect(() => {
    if (!query.trim()) {
      setResults({ cloud: [], archives: [] })
      return
    }

    let active = true
    ;(async () => {
      setLoading(true)
      setError('')
      try {
        const data = await searchTracks(query, tab, page)
        if (active) {
          setResults({ cloud: data.cloud, archives: data.archives })
        }
      } catch (err) {
        if (active) {
          setError(err.message)
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    })()

    return () => {
      active = false
    }
  }, [query, tab, page])

  const pagination = useMemo(() => {
    const cap = 100
    const pages = []
    for (let i = 1; i <= cap && i <= 3 + page; i += 1) {
      pages.push(i)
    }
    return pages
  }, [page])

  return (
    <div>
      <div className="mb-4 rounded-xl border border-white/10 bg-white/5 p-3 text-sm text-zinc-300">
        <p className="mb-2 font-medium text-zinc-200">Suggestions</p>
        <div className="grid gap-2 md:grid-cols-2">
          <div>
            <p className="mb-1 text-xs uppercase text-zinc-500">Songs</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.songs.map((song) => (
                <button key={song} type="button" onClick={() => setQuery(song)} className="rounded bg-white/10 px-2 py-1 text-xs">
                  {song}
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="mb-1 text-xs uppercase text-zinc-500">Artists</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.artists.map((artist) => (
                <button key={artist} type="button" onClick={() => setQuery(artist)} className="rounded bg-white/10 px-2 py-1 text-xs">
                  {artist}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="mb-4 flex gap-2">
        {tabs.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => {
              setTab(item)
              setPage(1)
            }}
            className={`rounded-full px-3 py-1 text-sm capitalize ${
              tab === item ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white' : 'bg-white/10 text-zinc-300'
            }`}
          >
            {item}
          </button>
        ))}
      </div>

      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

      <AnimatePresence mode="wait">
        <motion.div
          key={`${tab}-${page}`}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.2 }}
          className="space-y-8"
        >
          <section>
            <h2 className="mb-3 text-lg font-semibold text-white">Results from NLS Cloud</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {loading
                ? Array.from({ length: 8 }).map((_, index) => <SkeletonCard key={index} />)
                : results.cloud.map((track) => (
                    <TrackCard
                      key={track.id}
                      track={track}
                      onPlay={onPlay}
                      onDownload={downloadTrack}
                      isPlaying={playing && currentTrack?.id === track.id}
                    />
                  ))}
            </div>
          </section>

          <section>
            <h2 className="mb-3 text-lg font-semibold text-white">Results from NLS Archives</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {loading
                ? Array.from({ length: 4 }).map((_, index) => <SkeletonCard key={index} />)
                : results.archives.map((track) => (
                    <TrackCard
                      key={track.id}
                      track={track}
                      onPlay={onPlay}
                      onDownload={downloadTrack}
                      isPlaying={playing && currentTrack?.id === track.id}
                    />
                  ))}
            </div>
          </section>
        </motion.div>
      </AnimatePresence>

      <div className="mt-6 flex flex-wrap items-center gap-2 pb-24">
        {pagination.map((number) => (
          <button
            key={number}
            type="button"
            onClick={() => setPage(number)}
            className={`rounded px-3 py-1 text-sm ${page === number ? 'bg-white text-black' : 'bg-white/10 text-zinc-300'}`}
          >
            {number}
          </button>
        ))}
        <button type="button" onClick={() => setPage((current) => current + 1)} className="rounded bg-white/10 px-3 py-1 text-sm">
          Next
        </button>
      </div>
    </div>
  )
}
