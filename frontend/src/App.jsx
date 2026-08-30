import { useState, useCallback, useRef, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import Seal from "./Seal";
import TrustDial from "./TrustDial";
import Icon from "./Icon";
import ActivityLog from "./ActivityLog";
import useAuditRun from "./useAuditRun";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [protectedAttribute, setProtectedAttribute] = useState("");
  const [privilegedValue, setPrivilegedValue] = useState("");
  const [positiveOutcomeValue, setPositiveOutcomeValue] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const resultsRef = useRef(null);

  const audit = useAuditRun(API_BASE_URL);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }, []);

  const runAudit = () => {
    if (!file) return;
    audit.run(file, { protectedAttribute, privilegedValue, positiveOutcomeValue });
  };

  const retryAudit = () => {
    audit.reset();
    if (file) {
      setTimeout(() => audit.run(file, { protectedAttribute, privilegedValue, positiveOutcomeValue }), 50);
    }
  };

  useEffect(() => {
    if (audit.result) {
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    }
  }, [audit.result]);

  const downloadReport = () => {
    if (!audit.result?.report_id) return;
    window.open(`${API_BASE_URL}/api/report/${audit.result.report_id}`, "_blank");
  };

  const scrollToUpload = () => {
    document.getElementById("upload-section")?.scrollIntoView({ behavior: "smooth" });
  };

  const result = audit.result;
  const dirScore = result?.bias_detection?.disparate_impact;
  const eodScore = result?.bias_detection?.equal_opportunity;
  const features = result?.explainability?.top_features || [];

  const autoDetectParts = (() => {
    const ad = result?.config_used?.auto_detect;
    if (!ad) return [];
    const parts = [];
    if (ad.protected_attribute)
      parts.push(`attribute = ${result.config_used.protected_attribute}`);
    if (ad.privileged_value)
      parts.push(`privileged = ${result.config_used.privileged_value}`);
    if (ad.positive_outcome_value)
      parts.push(`positive outcome = ${result.config_used.positive_outcome_value}`);
    return parts;
  })();

  return (
    <div className="app">

      {/* ── Top bar ──────────────────────────────────────────────────── */}
      <nav className="topbar">
        <div className="topbar-inner">
          <div className="topbar-brand">
            <img
              src="/logo/lockup_horizontal.png"
              alt="Insaaf AI"
              className="topbar-lockup"
            />
          </div>
          <div className="topbar-meta">
            <span className="topbar-tag">AI Accountability Auditor</span>
          </div>
        </div>
      </nav>

      {/* ── Main content ─────────────────────────────────────────────── */}
      <main className="main-content">

        {/* ── Hero ──────────────────────────────────────────────────── */}
        <section className="hero">
          <div className="hero-inner">
            <div className="hero-copy">
              <p className="hero-eyebrow">Bias Audit Platform</p>
              <h1 className="hero-title">
                Audit AI systems for <em>fairness</em> and accountability.
              </h1>
              <p className="hero-sub">
                Upload decision data from any AI system. Insaaf AI tests it against
                published fairness standards and issues a bilingual compliance
                report in minutes.
              </p>
              <button className="btn btn-primary btn-lg" onClick={scrollToUpload}>
                Start an audit
                <Icon name="chevronRight" size={16} />
              </button>
            </div>
            <div className="hero-visual">
              <div className="hero-cards">
                <div className="preview-card preview-card--back">
                  <div className="preview-mini-header">
                    <Icon name="barChart3" size={14} stroke="var(--text-muted)" />
                    <span className="preview-label">Feature Impact</span>
                  </div>
                  <div className="preview-bars">
                    <div className="preview-bar">
                      <span className="preview-bar-label">income</span>
                      <div className="preview-bar-track"><div className="preview-bar-fill" style={{ width: "85%" }} /></div>
                    </div>
                    <div className="preview-bar">
                      <span className="preview-bar-label">city</span>
                      <div className="preview-bar-track"><div className="preview-bar-fill" style={{ width: "60%" }} /></div>
                    </div>
                    <div className="preview-bar">
                      <span className="preview-bar-label">gender</span>
                      <div className="preview-bar-track"><div className="preview-bar-fill preview-bar-fill--warn" style={{ width: "35%" }} /></div>
                    </div>
                  </div>
                </div>
                <div className="preview-card preview-card--front">
                  <div className="preview-header">
                    <span className="preview-label">Trust Report</span>
                    <span className="preview-badge preview-badge-pass">Certified</span>
                  </div>
                  <div className="preview-score-row">
                    <div className="preview-dial">
                      <TrustDial score={82} size={80} />
                    </div>
                    <div className="preview-metrics">
                      <div className="preview-metric">
                        <span className="preview-metric-label">DIR</span>
                        <span className="preview-metric-value">0.87</span>
                      </div>
                      <div className="preview-metric">
                        <span className="preview-metric-label">EOD</span>
                        <span className="preview-metric-value">0.02</span>
                      </div>
                    </div>
                  </div>
                  <div className="preview-comparison">
                    Comparing: male vs. female
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ── Upload section ────────────────────────────────────────── */}
        <section className="section" id="upload-section">
          <div className="section-header">
            <div className="section-eyebrow">
              <span className="section-index">01</span>
              <span className="section-rule" aria-hidden="true" />
            </div>
            <h2 className="section-title">Upload dataset</h2>
            <p className="section-desc">
              CSV with at least one protected attribute (gender, age, city) and one outcome column (approved / rejected).
            </p>
          </div>

          <div
            className={`upload-card ${dragActive ? "drag-active" : ""}`}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <div className="upload-zone">
              {file ? (
                <div className="file-ready">
                  <div className="file-ready-icon">
                    <Icon name="fileText" size={32} stroke="var(--accent)" />
                  </div>
                  <div className="file-ready-info">
                    <span className="file-ready-name">{file.name}</span>
                    <span className="file-ready-size">{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                  <button
                    className="file-clear"
                    onClick={() => setFile(null)}
                    title="Remove file"
                  >
                    <Icon name="x" size={16} />
                  </button>
                </div>
              ) : (
                <div className="drop-prompt">
                  <div className="drop-icon-badge">
                    <Icon name="upload" size={28} stroke="var(--accent)" />
                  </div>
                  <p className="drop-text">Drop your CSV file here</p>
                  <p className="drop-or">or</p>
                </div>
              )}

              <div className="upload-actions">
                <label className="btn btn-outline" htmlFor="file-input">
                  Choose file
                </label>
                <input
                  id="file-input"
                  type="file"
                  accept=".csv"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <button
                  className="btn btn-primary"
                  onClick={runAudit}
                  disabled={!file || audit.loading}
                >
                  {audit.loading ? (
                    <>
                      <span className="spinner" />
                      Analysing…
                    </>
                  ) : (
                    "Run audit"
                  )}
                </button>
              </div>
            </div>

            {/* Advanced options */}
            <div className="adv-section">
              <button
                className="adv-toggle"
                onClick={() => setAdvancedOpen((v) => !v)}
                aria-expanded={advancedOpen}
              >
                <Icon name={advancedOpen ? "chevronDown" : "chevronRight"} size={14} />
                Advanced options
              </button>

              {advancedOpen && (
                <div className="adv-grid">
                  <div className="field">
                    <label htmlFor="pa">Protected attribute</label>
                    <input
                      id="pa"
                      placeholder="auto-detect"
                      value={protectedAttribute}
                      onChange={(e) => setProtectedAttribute(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="pv">Privileged value</label>
                    <input
                      id="pv"
                      placeholder="e.g. male or Lahore,Karachi"
                      value={privilegedValue}
                      onChange={(e) => setPrivilegedValue(e.target.value)}
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="pov">Positive outcome value</label>
                    <input
                      id="pov"
                      placeholder="e.g. approved"
                      value={positiveOutcomeValue}
                      onChange={(e) => setPositiveOutcomeValue(e.target.value)}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {audit.error && (
            <div className="error-card">
              <Icon name="alertCircle" size={18} stroke="var(--danger)" />
              <div className="error-card-content">
                {audit.errorStage && (
                  <span className="error-stage">Failed at: {audit.errorStage}</span>
                )}
                <span>{audit.error}</span>
              </div>
              <button className="btn btn-outline btn-sm" onClick={retryAudit}>
                <Icon name="refreshCw" size={14} />
                Retry
              </button>
            </div>
          )}
        </section>

        {/* ── Activity log ──────────────────────────────────────────── */}
        {audit.showLog && (
          <section className="section">
            <ActivityLog
              stageStatus={audit.stageStatus}
              log={audit.log}
              phase={audit.phase}
              error={audit.error}
              onRetry={retryAudit}
            />
          </section>
        )}

        {/* ── Results ───────────────────────────────────────────────── */}
        {result && (
          <div className="results-wrapper" ref={resultsRef}>

            {/* Verdict */}
            <section className="section">
              <div className="section-header">
                <div className="section-eyebrow">
                  <span className="section-index">02</span>
                  <span className="section-rule" aria-hidden="true" />
                </div>
                <h2 className="section-title">Audit verdict</h2>
              </div>
              <div className="card verdict-card">
                <div className="verdict-layout">
                  <div className="verdict-dial-col">
                    <TrustDial score={result.report.trust_score} />
                  </div>
                  <div className="verdict-info-col">
                    <span className={`status-badge ${result.report.certified ? "pass" : "fail"}`}>
                      <Icon
                        name={result.report.certified ? "check" : "alertCircle"}
                        size={14}
                      />
                      {result.report.certified ? "Certified fair" : "Bias flagged"}
                    </span>
                    <h3 className="verdict-headline">
                      {result.bias_detection.bias_detected
                        ? "This system shows measurable bias."
                        : "This system passed the fairness checks tested."}
                    </h3>
                    <p className="verdict-detail">
                      Audited against <strong>{result.config_used.protected_attribute}</strong> using{" "}
                      <strong>{result.config_used.outcome_column}</strong> as the outcome,
                      across {result.intake.row_count.toLocaleString()} records.
                    </p>
                    {result.report.group_comparison && (
                      <p className="group-comparison">
                        {result.report.group_comparison.en}
                      </p>
                    )}
                    {autoDetectParts.length > 0 && (
                      <p className="auto-detect-note">
                        <Icon name="info" size={12} />
                        Auto-detected: {autoDetectParts.join(", ")}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Findings */}
            <section className="section">
              <div className="section-header">
                <div className="section-eyebrow">
                  <span className="section-index">03</span>
                  <span className="section-rule" aria-hidden="true" />
                </div>
                <h2 className="section-title">Fairness metrics</h2>
              </div>
              <div className="metrics-grid">
                <div className={`card metric-card ${dirScore?.passes_80_percent_rule ? "metric-card--pass" : "metric-card--fail"}`}>
                  <h4 className="metric-label">Disparate Impact Ratio</h4>
                  <p
                    className="metric-value"
                    style={{ color: dirScore?.passes_80_percent_rule ? "var(--success)" : "var(--danger)" }}
                  >
                    {dirScore?.score}
                  </p>
                  <p className="metric-detail">
                    {dirScore?.passes_80_percent_rule ? "Passes" : "Fails"} the 80% rule.
                    Privileged {(dirScore?.privileged_positive_rate * 100).toFixed(1)}% vs.
                    unprivileged {(dirScore?.unprivileged_positive_rate * 100).toFixed(1)}%.
                  </p>
                </div>
                <div className={`card metric-card ${eodScore?.within_acceptable_range ? "metric-card--pass" : eodScore ? "metric-card--fail" : ""}`}>
                  <h4 className="metric-label">Equal Opportunity Difference</h4>
                  {eodScore ? (
                    <>
                      <p
                        className="metric-value"
                        style={{ color: eodScore.within_acceptable_range ? "var(--success)" : "var(--danger)" }}
                      >
                        {eodScore.score}
                      </p>
                      <p className="metric-detail">
                        {eodScore.within_acceptable_range ? "Within" : "Outside"} the
                        accepted ±0.1 range between groups.
                      </p>
                    </>
                  ) : (
                    <p className="metric-detail metric-na">
                      Requires a ground-truth outcome column.
                    </p>
                  )}
                </div>
              </div>

              {features.length > 0 && (
                <div className="card chart-card">
                  <h4 className="metric-label">Top Contributing Features</h4>
                  <p className="chart-note">{result.explainability.note}</p>
                  <ResponsiveContainer width="100%" height={240}>
                    <BarChart data={features} layout="vertical" margin={{ left: 10, right: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                      <XAxis
                        type="number"
                        tick={{ fontFamily: "IBM Plex Mono", fontSize: 11, fill: "#6B7280" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <YAxis
                        type="category"
                        dataKey="feature"
                        width={100}
                        tick={{ fontFamily: "IBM Plex Mono", fontSize: 12, fill: "#374151" }}
                        axisLine={false}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: "var(--surface-card)",
                          border: "1px solid var(--border)",
                          borderRadius: "var(--r-sm)",
                          fontFamily: "var(--font-mono)",
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                        {features.map((f, i) => (
                          <Cell
                            key={i}
                            fill={
                              f.feature === result.config_used.protected_attribute
                                ? "var(--danger)"
                                : "var(--accent)"
                            }
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </section>

            {/* Bilingual Report */}
            <section className="section">
              <div className="section-header">
                <div className="section-eyebrow">
                  <span className="section-index">04</span>
                  <span className="section-rule" aria-hidden="true" />
                </div>
                <h2 className="section-title">Compliance report</h2>
              </div>
              <div className="report-grid">
                <div className="card report-col report-en">
                  <h4 className="report-lang-label">English</h4>
                  <p className="report-text">{result.report.summary_english}</p>
                </div>
                <div className="card report-col report-ur">
                  <h4 className="report-lang-label">اردو</h4>
                  <p className="report-text report-text-ur">{result.report.summary_urdu}</p>
                </div>
              </div>

              <div className="actions-bar">
                <Seal passed={result.report.certified} />
                <button className="btn btn-primary" onClick={downloadReport}>
                  <Icon name="download" size={16} />
                  Download PDF report
                </button>
              </div>
            </section>

          </div>
        )}

      </main>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="footer">
        <span>Insaaf AI</span>
        <span>Alibaba Cloud AI Hackathon Pakistan 2026</span>
      </footer>

    </div>
  );
}

export default App;
