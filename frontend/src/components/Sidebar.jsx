import { Disc3, Download, Home, Library, ListMusic, Search } from 'lucide-react'

const links = [
  { to: '/', label: 'Home', icon: Home },
  { to: '/discover', label: 'Discover', icon: Search },
  { to: '/library', label: 'Library', icon: Library },
  { to: '/downloads', label: 'Downloads', icon: Download },
  { to: '/playlists', label: 'Playlists', icon: ListMusic },
]

export default function Sidebar({ currentPath, onNavigate }) {
  return (
    <aside className="w-full border-b border-white/10 bg-white/5 p-4 backdrop-blur-xl md:min-h-screen md:w-64 md:border-b-0 md:border-r">
      <div className="mb-6 flex items-center gap-2 text-xl font-semibold text-white">
        <Disc3 className="text-purple-400" /> NLSmusic
      </div>
      <nav className="flex gap-2 overflow-auto md:flex-col">
        {links.map(({ to, label, icon: Icon }) => (
          <a
            key={to}
            href={to}
            onClick={(event) => {
              event.preventDefault()
              onNavigate(to)
            }}
            className={`flex min-w-max items-center gap-2 rounded-xl px-4 py-2 transition ${
              currentPath === to ? 'bg-gradient-to-r from-purple-500 to-blue-500 text-white' : 'text-zinc-300 hover:bg-white/10'
            }`}
          >
            <Icon size={16} /> {label}
          </a>
        ))}
      </nav>
    </aside>
  )
}
