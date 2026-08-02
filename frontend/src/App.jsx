import { useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import Player from './components/Player'
import Sidebar from './components/Sidebar'
import { downloadTrack } from './lib/api'
import DownloadsPage from './pages/DownloadsPage'
import PlaceholderPage from './pages/PlaceholderPage'
import SearchPage from './pages/SearchPage'

const STREAM_URL = import.meta.env.VITE_STREAM_SAMPLE || 'https://archive.org/download/testmp3testfile/mpthreetest.mp3'

function normalizePath(pathname) {
  return pathname === '/' ? '/search' : pathname
}

export default function App() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname))
  const [query, setQuery] = useState('')
  const [currentTrack, setCurrentTrack] = useState(null)
  const [playing, setPlaying] = useState(false)
  const audioRef = useRef(new Audio(STREAM_URL))

  useEffect(() => {
    const onPop = () => setPath(normalizePath(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  const onNavigate = (nextPath) => {
    const normalized = normalizePath(nextPath)
    window.history.pushState({}, '', normalized)
    setPath(normalized)
  }

  const onQueryChange = (value) => {
    setQuery(value)
    if (path !== '/search') {
      onNavigate('/search')
    }
  }

  const onPlay = (track) => {
    setCurrentTrack(track)
    if (playing) {
      audioRef.current.pause()
      setPlaying(false)
      return
    }
    audioRef.current.play().catch(() => null)
    setPlaying(true)
  }

  const onToggle = () => {
    if (!playing) {
      audioRef.current.play().catch(() => null)
      setPlaying(true)
      return
    }
    audioRef.current.pause()
    setPlaying(false)
  }

  const renderPage = () => {
    if (path === '/search') {
      return (
        <SearchPage query={query} setQuery={onQueryChange} onPlay={onPlay} currentTrack={currentTrack} playing={playing} />
      )
    }
    if (path === '/discover') {
      return <PlaceholderPage title="Discover" />
    }
    if (path === '/library') {
      return <PlaceholderPage title="Library" />
    }
    if (path === '/downloads') {
      return <DownloadsPage />
    }
    if (path === '/playlists') {
      return <PlaceholderPage title="Playlists" />
    }
    return <PlaceholderPage title="Not Found" />
  }

  return (
    <div className="flex min-h-screen flex-col md:flex-row">
      <Sidebar currentPath={path} onNavigate={onNavigate} />
      <main className="flex-1 p-4">
        <Header query={query} onQueryChange={onQueryChange} />
        {renderPage()}
      </main>
      <Player track={currentTrack} playing={playing} onToggle={onToggle} onDownload={downloadTrack} />
    </div>
  )
}
