import { Activity, Check, Circle, AlertCircle, Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { AUDIT_STAGES } from "./auditStream";
import { cn } from "@/lib/utils";

const statusIcon = {
  pending: Circle,
  running: Loader2,
  done: Check,
  error: AlertCircle,
  skipped: Circle,
};

const statusClass = {
  pending: "text-muted-foreground opacity-50",
  running: "text-primary",
  done: "text-emerald-600",
  error: "text-destructive",
  skipped: "text-border opacity-40",
};

export default function ActivityLog({ stageStatus, log, phase, error, onRetry }) {
  const total = AUDIT_STAGES.length;
  const doneCount = AUDIT_STAGES.filter((s) => stageStatus[s.key] === "done").length;
  const progressPct = total > 0 ? (doneCount / total) * 100 : 0;
  const isFinished = phase === "complete" || phase === "error";

  return (
    <div
      className={cn(
        "rounded-xl border border-border bg-card p-6 shadow-sm transition-opacity",
        isFinished && "opacity-80"
      )}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-[18px] h-[18px] text-primary" />
          <span className="font-mono text-xs font-semibold uppercase tracking-wide text-secondary-foreground">
            Audit progress
          </span>
        </div>
        <span className="font-mono text-xs text-muted-foreground tabular-nums">
          {doneCount}/{total}
        </span>
      </div>

      <Progress value={progressPct} className="h-1.5 mb-5" />

      <ol
        className="relative space-y-0"
        aria-live="polite"
        aria-busy={phase === "streaming" || phase === "legacy"}
      >
        <li
          className="absolute left-[11px] top-2 bottom-2 w-px bg-border"
          aria-hidden="true"
        />
        {AUDIT_STAGES.map((stage, i) => {
          const status = stageStatus[stage.key] || "pending";
          const logEntry = log.find((r) => r.key === stage.key);
          const label = logEntry?.label || stage.label;
          const Icon = statusIcon[status];

          return (
            <li
              key={stage.key}
              className={cn(
                "relative grid grid-cols-[24px_1fr] gap-3 items-center py-2",
                status === "running" && "opacity-100",
                status === "pending" && "opacity-50",
                status === "skipped" && "opacity-40"
              )}
              style={{ animationDelay: `${i * 60}ms` }}
              aria-current={status === "running" ? "step" : undefined}
            >
              <span
                className={cn(
                  "z-10 flex items-center justify-center w-6 h-6 rounded-full bg-card",
                  status === "running" && "animate-pulse"
                )}
              >
                <Icon
                  className={cn(
                    "w-3.5 h-3.5",
                    status === "running" && "animate-spin",
                    statusClass[status]
                  )}
                />
              </span>
              <span
                className={cn(
                  "text-sm",
                  status === "done" && "text-secondary-foreground",
                  status === "error" && "text-destructive font-medium",
                  status !== "done" && status !== "error" && "text-foreground"
                )}
              >
                {label}
              </span>
              <span className="sr-only">{status}</span>
            </li>
          );
        })}
      </ol>

      {phase === "error" && error && (
        <div className="flex items-center gap-3 mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-sm text-destructive">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span className="flex-1 leading-snug">{error}</span>
          {onRetry && (
            <button
              onClick={onRetry}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-destructive/30 bg-background hover:bg-destructive/5 text-xs font-medium transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}
