import { Link } from 'react-router-dom'
import { AGENT_ORDER, AGENT_ROLES } from '../lib/agents'
import { departmentOf } from '../lib/departments'
import './SystemAdminPage.css'

/* ניהול מערכת — עמוד-בית לנושאים שקשורים לתפעול והגדרת המערכת (לא לשוטף).
   בנוי כאוסף "כרטיסי נושא"; מוסיפים נושא חדש = עוד <section className="admin-card">. */
export default function SystemAdminPage() {
  return (
    <div className="admin-page">
      <div className="container">
        <div className="admin-head">
          <span className="admin-eyebrow">company framework<i /></span>
          <h1 className="admin-title">ניהול מערכת</h1>
          <p className="admin-note">
            נושאים שקשורים להגדרה ולתחזוקה של המערכת — לא לפעילות השוטפת.
          </p>
        </div>

        {/* נושא: סוכנים ותפקידים */}
        <section className="admin-card">
          <header className="admin-card-head">
            <h2 className="admin-card-title">סוכנים ותפקידים</h2>
            <Link to="/comms" className="admin-card-link">לחדרי השיחה ←</Link>
          </header>
          <div className="admin-tablewrap">
            <table className="admin-table">
              <thead>
                <tr><th>סוכן</th><th>תפקיד</th><th>מחלקה</th></tr>
              </thead>
              <tbody>
                {AGENT_ORDER.map((name) => (
                  <tr key={name}>
                    <td className="cell-name">{name}</td>
                    <td><span className="role-pill">{AGENT_ROLES[name]}</span></td>
                    <td className="cell-dept">{departmentOf(name)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  )
}
