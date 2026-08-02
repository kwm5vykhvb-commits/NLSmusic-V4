import { Download, Pause, Play } from 'lucide-react'
import { motion } from 'framer-motion'

export default function TrackCard({ track, onPlay, onDownload, isPlaying }) {
  return (
    <motion.article
      whileHover={{ scale: 1.03 }}
      transition={{ duration: 0.2 }}
      className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-xl"
    >
      <div className="mb-4 h-30 rounded-xl bg-gradient-to-br from-purple-500/60 to-blue-500/60" />
      <h3 className="truncate font-medium text-white">{track.title}</h3>
      <p className="truncate text-sm text-zinc-400">{track.artist}</p>
      <p className="text-xs text-zinc-500">{track.duration}</p>
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => onPlay(track)}
          className="flex items-center gap-1 rounded-lg bg-white/10 px-3 py-1 text-sm hover:bg-white/20"
        >
          {isPlaying ? <Pause size={14} /> : <Play size={14} />} {isPlaying ? 'Pause' : 'Play'}
        </button>
        <button
          type="button"
          onClick={() => onDownload(track.id)}
          className="flex items-center gap-1 rounded-lg bg-gradient-to-r from-purple-500 to-blue-500 px-3 py-1 text-sm text-white"
        >
          <Download size={14} /> Download
        </button>
      </div>
    </motion.article>
  )
}
