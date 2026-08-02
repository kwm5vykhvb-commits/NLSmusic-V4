import { Search } from 'lucide-react'

export default function Header({ query, onQueryChange }) {
  return (
    <header className="sticky top-0 z-10 mb-4 flex items-center justify-between gap-3 border-b border-white/10 bg-[#050505]/80 p-4 backdrop-blur">
      <label className="flex w-full max-w-xl items-center gap-2 rounded-xl border border-white/10 bg-white/5 px-3 py-2">
        <Search size={16} className="text-zinc-400" />
        <input
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder="Search songs and artists"
          className="w-full bg-transparent text-sm text-zinc-100 outline-none"
        />
      </label>
      <div className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-r from-purple-500 to-blue-500 text-sm font-semibold text-white">
        U
      </div>
    </header>
  )
}
