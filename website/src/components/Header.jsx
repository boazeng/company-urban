import { Link, useLocation } from 'react-router-dom'
import TactLogo from './TactLogo'
import './Header.css'

const navItems = [
  { path: '/structure', label: 'מבנה חברה' },
  { path: '/processes', label: 'תהליכים' },
  { path: '/timeline', label: 'לוח זמנים' },
  { path: '/calendar', label: 'יומן שבועי' },
  { path: '/goals', label: 'יעדים' },
  { path: '/comms', label: 'תקשורת' },
  { path: '/interfaces', label: 'ממשקים' },
]

export default function Header() {
  const location = useLocation()
  const current = location.pathname === '/' ? '/structure' : location.pathname

  return (
    <header className="header">
      <div className="container header-inner">
        <Link to="/" className="header-logo" aria-label="company framework">
          <TactLogo tone="light" size={0.82} />
        </Link>

        <nav className="header-nav">
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`header-nav-link ${current.startsWith(item.path) ? 'active' : ''}`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
