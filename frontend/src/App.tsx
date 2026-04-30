import { NavLink, Routes, Route } from "react-router-dom";
import "./App.css";
import MlAdvisor from "./components/MlAdvisor";
import DlpDiagnostics from "./components/dlp/DlpDiagnostics";
import FileActivityTimelineDemo from "./components/dlp/FileActivityTimelineDemo";

function App() {
  return (
    <div className="app">
      <nav className="app-nav">
        <NavLink to="/" end>
          🧠 ML Advisor
        </NavLink>
        <NavLink to="/dlp">🔍 DLP Diagnostics</NavLink>
        <NavLink to="/dlp/timeline">📅 File Timeline</NavLink>
      </nav>

      <Routes>
        <Route path="/" element={<MlAdvisor />} />
        <Route path="/dlp" element={<DlpDiagnostics />} />
        <Route path="/dlp/timeline" element={<FileActivityTimelineDemo />} />
      </Routes>
    </div>
  );
}

export default App;
