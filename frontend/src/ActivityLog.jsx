import Icon from "./Icon";
import { AUDIT_STAGES } from "./auditStream";
import "./ActivityLog.css";

export default function ActivityLog({ stageStatus, log, phase, error, onRetry }) {
  const total = AUDIT_STAGES.length;
  const doneCount = AUDIT_STAGES.filter((s) => stageStatus[s.key] === "done").length;
  const progressPct = total > 0 ? (doneCount / total) * 100 : 0;
  const isFinished = phase === "complete" || phase === "error";

  return (
    <div className="activity-card card">
      <div className="activity-header">
        <div className="activity-header-left">
          <Icon name="activity" size={18} stroke="var(--accent)" />
          <span className="activity-title">Audit progress</span>
        </div>
        <span className="activity-counter">
          {doneCount}/{total}
        </span>
      </div>

      <div className="activity-progress-track">
        <div
          className="activity-progress-bar"
          style={{ width: `${progressPct}%` }}
        />
      </div>

      <ol
        className={`activity-log ${isFinished ? "activity-log--finished" : ""}`}
        aria-live="polite"
        aria-busy={phase === "streaming" || phase === "legacy"}
      >
        {AUDIT_STAGES.map((stage, i) => {
          const status = stageStatus[stage.key] || "pending";
          const logEntry = log.find((r) => r.key === stage.key);
          const label = logEntry?.label || stage.label;

          return (
            <li
              key={stage.key}
              className={`activity-row activity-row--${status}`}
              style={{ "--i": i }}
              aria-current={status === "running" ? "step" : undefined}
            >
              <span className="activity-icon">
                {status === "pending" && (
                  <Icon name="circle" size={14} stroke="var(--text-muted)" />
                )}
                {status === "running" && <span className="activity-spinner" />}
                {status === "done" && (
                  <Icon name="check" size={14} stroke="var(--success)" />
                )}
                {status === "error" && (
                  <Icon name="alertCircle" size={14} stroke="var(--danger)" />
                )}
                {status === "skipped" && (
                  <Icon name="circle" size={14} stroke="var(--border-strong)" />
                )}
              </span>
              <span className="activity-label">{label}</span>
              <span className="sr-only">{status}</span>
            </li>
          );
        })}
      </ol>

      {phase === "error" && error && (
        <div className="activity-error">
          <Icon name="alertCircle" size={16} stroke="var(--danger)" />
          <span className="activity-error-text">{error}</span>
          {onRetry && (
            <button className="btn btn-outline btn-sm" onClick={onRetry}>
              <Icon name="refreshCw" size={14} />
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
