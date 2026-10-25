import { WindReplayPage } from './features/wind-replay/WindReplayPage'

export default function App() {
  return <div className="shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark">✳</span><span>GridBricks <small>pilot</small></span></div>
      <div className="side-label">WORKSPACE</div>
      <div className="nav active">▥ <span>Wind decision replay</span></div>
      <div className="side-footer"><span className="status-dot" /> Historic pilot · January 2026</div>
    </aside>
    <main className="main">
      <header className="topbar">
        <div className="breadcrumb">Energy intelligence <span>/</span> Forecast performance</div>
        <div className="pill">Elexon BMRS data</div>
      </header>
      <WindReplayPage />
    </main>
  </div>
}
