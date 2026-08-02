import { useEffect, useRef, useState } from 'react'
import Header from './components/Header'
import Player from './components/Player'
import Sidebar from './components/Sidebar'
import { downloadTrack, streamTrackUrl } from './lib/api'
import DownloadsPage from './pages/DownloadsPage'
import PlaceholderPage from './pages/PlaceholderPage'
import SearchPage from './pages/SearchPage'

function normalizePath(pathname) {
  return pathname === '/' ? '/search' : pathname
}

export default function App() {
  const [path, setPath] = useState(() => normalizePath(window.location.pathname))
  const [query, setQuery] = useState('')
  const [currentTrack, setCurrentTrack] = useState(null)
  const [playing, setPlaying] = useState(false)
  const [progress, setProgress] = useState({ currentTime: 0, duration: 0 })
  const audioRef = useRef(new Audio())

  useEffect(() => {
    const onPop = () => setPath(normalizePath(window.location.pathname))
    window.addEventListener('popstate', onPop)
    return () => window.removeEventListener('popstate', onPop)
  }, [])

  useEffect(() => {
    const audio = audioRef.current
    const onTimeUpdate = () => setProgress({ currentTime: audio.currentTime, duration: audio.duration || 0 })
    const onEnded = () => setPlaying(false)
    audio.addEventListener('timeupdate', onTimeUpdate)
    audio.addEventListener('loadedmetadata', onTimeUpdate)
    audio.addEventListener('ended', onEnded)
    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate)
      audio.removeEventListener('loadedmetadata', onTimeUpdate)
      audio.removeEventListener('ended', onEnded)
    }
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
    const audio = audioRef.current

    if (currentTrack?.id === track.id) {
      if (playing) {
        audio.pause()
        setPlaying(false)
      } else {
        audio.play().catch(() => null)
        setPlaying(true)
      }
      return
    }

    setCurrentTrack(track)
    setProgress({ currentTime: 0, duration: 0 })
    audio.pause()
    audio.src = streamTrackUrl(track.id)
    audio.currentTime = 0
    audio.play().catch(() => null)
    setPlaying(true)
  }

  const onToggle = () => {
    if (!currentTrack) {
      return
    }
    const audio = audioRef.current
    if (!playing) {
      audio.play().catch(() => null)
      setPlaying(true)
      return
    }
    audio.pause()
    setPlaying(false)
  }

  const onSeek = (time) => {
    audioRef.current.currentTime = time
    setProgress((current) => ({ ...current, currentTime: time }))
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
      <Player
        track={currentTrack}
        playing={playing}
        progress={progress}
        onToggle={onToggle}
        onSeek={onSeek}
        onDownload={downloadTrack}
      />
    </div>
  )
}

