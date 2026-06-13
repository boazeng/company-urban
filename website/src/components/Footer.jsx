import './Footer.css'

export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <span className="footer-mark">
          {['T', 'A', 'C', 'T'].map((l, i) => (
            <span key={i} className="footer-seg">
              <span className="footer-letter">{l}</span>
              {i < 3 && <span className="footer-dot" />}
            </span>
          ))}
        </span>
        <span className="footer-tagline">company framework</span>
      </div>
    </footer>
  )
}
