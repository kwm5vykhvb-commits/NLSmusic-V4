import { Download, Pause, Play, SkipBack, SkipForward, Volume2 } from 'lucide-react'

export default function Player({ track, playing, onToggle, onDownload }) {
  return (
    <div className="fixed bottom-0 left-0 right-0 border-t border-white/10 bg-black/80 px-4 py-3 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-sm text-white">{track?.title || 'Select a song'}</p>
          <p className="truncate text-xs text-zinc-400">{track?.artist || 'NLSmusic'}</p>
        </div>
        <div className="flex items-center gap-2 text-zinc-100">
          <button type="button" className="rounded-full bg-white/10 p-2">
            <SkipBack size={15} />
          </button>
          <button type="button" onClick={onToggle} className="rounded-full bg-white/20 p-2">
            {playing ? <Pause size={15} /> : <Play size={15} />}
          </button>
          <button type="button" className="rounded-full bg-white/10 p-2">
            <SkipForward size={15} />
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
  )
}
