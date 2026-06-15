import { Routes, Route, useLocation } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import AppPage from './app/AppPage'
import StructurePage from './pages/StructurePage'
import TimelinePage from './pages/TimelinePage'
import CalendarPage from './pages/CalendarPage'
import InterfacesPage from './pages/InterfacesPage'
import GoalsPage from './pages/GoalsPage'
import CommsPage from './pages/CommsPage'
import AgentPage from './pages/AgentPage'
import SystemAdminPage from './pages/SystemAdminPage'
import PlaceholderPage from './pages/PlaceholderPage'

export default function App() {
  const { pathname } = useLocation()

  // the mobile "app" (/app) is a standalone full-screen shell — no desktop chrome.
  if (pathname === '/app' || pathname.startsWith('/app/')) {
    return (
      <Routes>
        <Route path="/app" element={<AppPage />} />
      </Routes>
    )
  }

  return (
    <>
      <Header />
      <main>
        <Routes>
          <Route path="/" element={<StructurePage />} />
          <Route path="/structure" element={<StructurePage />} />
          <Route path="/processes" element={<PlaceholderPage title="תהליכים" />} />
          <Route path="/timeline" element={<TimelinePage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/goals" element={<GoalsPage />} />
          <Route path="/comms" element={<CommsPage />} />
          <Route path="/agent/:slug" element={<AgentPage />} />
          <Route path="/interfaces" element={<InterfacesPage />} />
          <Route path="/admin" element={<SystemAdminPage />} />
          <Route path="*" element={<StructurePage />} />
        </Routes>
      </main>
      <Footer />
    </>
  )
}
