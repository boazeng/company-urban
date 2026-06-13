import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Footer from './components/Footer'
import StructurePage from './pages/StructurePage'
import TimelinePage from './pages/TimelinePage'
import CalendarPage from './pages/CalendarPage'
import InterfacesPage from './pages/InterfacesPage'
import GoalsPage from './pages/GoalsPage'
import CommsPage from './pages/CommsPage'
import SystemAdminPage from './pages/SystemAdminPage'
import PlaceholderPage from './pages/PlaceholderPage'

export default function App() {
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
          <Route path="/interfaces" element={<InterfacesPage />} />
          <Route path="/admin" element={<SystemAdminPage />} />
          <Route path="*" element={<StructurePage />} />
        </Routes>
      </main>
      <Footer />
    </>
  )
}
