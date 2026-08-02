import { Download, Pause, Play, Volume2 } from 'lucide-react'

function formatTime(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0:00'
  }
  const minutes = Math.floor(seconds / 60)
  const remaining = Math.floor(seconds % 60)
  return `${minutes}:${remaining.toString().padStart(2, '0')}`
}

export default function Player({ track, playing, progress, onToggle, onSeek, onDownload }) {
  const { currentTime = 0, duration = 0 } = progress || {}

  return (
    <div className="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-black/80 px-4 py-3 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-2">
        <div className="flex items-center gap-2">
          <span className="w-10 text-right text-xs text-zinc-400">{formatTime(currentTime)}</span>
          <input
            type="range"
            min={0}
            max={duration || 0}
            step={1}
            value={Math.min(currentTime, duration || 0)}
            onChange={(event) => onSeek(Number(event.target.value))}
            disabled={!track}
            className="h-1 flex-1 accent-purple-500 disabled:opacity-40"
          />
          <span className="w-10 text-xs text-zinc-400">{formatTime(duration)}</span>
        </div>
        <div className="flex items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-sm text-white">{track?.title || 'Select a song'}</p>
            <p className="truncate text-xs text-zinc-400">{track?.artist || 'NLSmusic'}</p>
          </div>
          <div className="flex items-center gap-2 text-zinc-100">
            <button
              type="button"
              onClick={onToggle}
              disabled={!track}
              className="rounded-full bg-white/20 p-2 disabled:opacity-40"
            >
              {playing ? <Pause size={15} /> : <Play size={15} />}
            </button>
            <Volume2 size={16} />
            {track && (
              <button
                type="button"
                onClick={() => onDownload(track.id)}
                className="rounded-full bg-gradient-to-r from-purple-500 to-blue-500 p-2"
              >
                <Download size={15} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
