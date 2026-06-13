import { Routes, Route, NavLink, useLocation } from 'react-router-dom'
import TactLogo from './components/TactLogo.jsx'
import HomePage from './pages/HomePage.jsx'
import BotFlowEditorPage from './pages/BotFlowEditor/BotFlowEditorPage.jsx'
import BotDiagnosticsPage from './pages/BotDiagnosticsPage.jsx'

const NAV = [
  { to: '/', label: 'דף הבית', end: true },
  { to: '/editor', label: 'עורך זרימה' },
  { to: '/diagnostics', label: 'אבחון שיחות' },
]

export default function App() {
  const location = useLocation()
  // The visual flow editor needs the full viewport, so hide the chrome there.
  const fullBleed = location.pathname.startsWith('/editor')

  return (
    <div className={`tact-aurora app-shell${fullBleed ? ' app-shell--editor' : ''}`}>
      <header className="tact-bar">
        <NavLink to="/" className="brand">
          <TactLogo size={1.4} word="bots" />
        </NavLink>
        <nav className="tact-nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>

      {fullBleed ? (
        <Routes>
          <Route path="/editor" element={<BotFlowEditorPage />} />
        </Routes>
      ) : (
        <main className="app-main">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/diagnostics" element={<BotDiagnosticsPage />} />
          </Routes>
        </main>
      )}
    </div>
  )
}
