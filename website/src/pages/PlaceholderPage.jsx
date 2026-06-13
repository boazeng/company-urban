import './PlaceholderPage.css'

/* Branded empty page for topics not yet built. */
export default function PlaceholderPage({ title }) {
  return (
    <div className="ph">
      <div className="container ph-inner">
        <span className="ph-eyebrow">company framework<i /></span>
        <h1 className="ph-title">{title}</h1>
        <span className="ph-badge">בבנייה</span>
      </div>
    </div>
  )
}
