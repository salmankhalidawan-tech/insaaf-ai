import { useReducer, useCallback, useRef, useEffect, useState } from "react";
import { AUDIT_STAGES, streamAudit, runAuditPlain, StreamUnsupportedError } from "./auditStream";

const STAGE_KEYS = AUDIT_STAGES.map((s) => s.key);

function initialStageStatus() {
  const s = {};
  for (const key of STAGE_KEYS) s[key] = "pending";
  return s;
}

const INITIAL = {
  phase: "idle",
  stageStatus: initialStageStatus(),
  log: [],
  result: null,
  error: null,
  errorStage: null,
};

function reducer(state, action) {
  switch (action.type) {
    case "START":
      return { ...INITIAL, phase: "streaming", stageStatus: initialStageStatus(), log: [] };

    case "EVENT": {
      const { stage, status, label } = action.payload;
      if (stage === "complete") return state;

      const idx = STAGE_KEYS.indexOf(stage);
      const next = { ...state.stageStatus };

      if (status === "running") {
        next[stage] = "running";
        for (let i = 0; i < idx; i++) {
          if (next[STAGE_KEYS[i]] === "running") next[STAGE_KEYS[i]] = "done";
          else if (next[STAGE_KEYS[i]] === "pending") next[STAGE_KEYS[i]] = "skipped";
        }
        const log = state.log.some((r) => r.key === stage)
          ? state.log.map((r) => (r.key === stage ? { ...r, label, status: "running" } : r))
          : [...state.log, { key: stage, label, status: "running", ts: Date.now() }];
        return { ...state, stageStatus: next, log };
      }

      if (status === "done") {
        next[stage] = "done";
        const log = state.log.some((r) => r.key === stage)
          ? state.log.map((r) => (r.key === stage ? { ...r, label, status: "done" } : r))
          : [...state.log, { key: stage, label, status: "done", ts: Date.now() }];
        return { ...state, stageStatus: next, log };
      }

      if (status === "error") {
        next[stage] = "error";
        const log = state.log.some((r) => r.key === stage)
          ? state.log.map((r) => (r.key === stage ? { ...r, label, status: "error" } : r))
          : [...state.log, { key: stage, label, status: "error", ts: Date.now() }];
        return {
          ...state,
          phase: "error",
          stageStatus: next,
          log,
          error: label || "Audit failed.",
          errorStage: stage,
        };
      }

      return state;
    }

    case "LEGACY":
      return {
        ...state,
        phase: "legacy",
        log: [{ key: "audit", label: "Running the audit", status: "running", ts: Date.now() }],
      };

    case "COMPLETE":
      return {
        ...state,
        phase: "complete",
        result: action.payload.result,
        log: state.log.map((r) => (r.status === "running" ? { ...r, status: "done" } : r)),
      };

    case "FAIL":
      return {
        ...state,
        phase: "error",
        error: action.payload.message,
        errorStage: action.payload.stage || null,
      };

    case "RESET":
      return { ...INITIAL, stageStatus: initialStageStatus() };

    default:
      return state;
  }
}

export default function useAuditRun(baseUrl) {
  const [state, dispatch] = useReducer(reducer, INITIAL);
  const abortRef = useRef(null);
  const [showLog, setShowLog] = useState(false);

  useEffect(() => {
    if (state.phase === "streaming" || state.phase === "legacy") {
      setShowLog(true);
    } else if (state.phase === "complete") {
      const timer = setTimeout(() => setShowLog(false), 450);
      return () => clearTimeout(timer);
    } else if (state.phase === "error") {
      setShowLog(true);
    } else {
      setShowLog(false);
    }
  }, [state.phase]);

  const run = useCallback(
    async (file, fields) => {
      if (abortRef.current) abortRef.current.abort();
      const controller = new AbortController();
      abortRef.current = controller;
      dispatch({ type: "START" });

      try {
        const result = await streamAudit({
          baseUrl,
          file,
          fields,
          signal: controller.signal,
          onEvent: (e) => dispatch({ type: "EVENT", payload: e }),
        });
        dispatch({ type: "COMPLETE", payload: { result } });
      } catch (err) {
        if (err.name === "AbortError") return;

        const shouldFallback =
          err instanceof StreamUnsupportedError ||
          (err instanceof TypeError && !err.sawEvent);

        if (shouldFallback) {
          dispatch({ type: "LEGACY" });
          try {
            const result = await runAuditPlain({
              baseUrl,
              file,
              fields,
              signal: controller.signal,
            });
            dispatch({ type: "COMPLETE", payload: { result } });
          } catch (e2) {
            if (e2.name === "AbortError") return;
            dispatch({ type: "FAIL", payload: { message: e2.message } });
          }
        } else {
          dispatch({
            type: "FAIL",
            payload: { message: err.message, stage: err.stage },
          });
        }
      }
    },
    [baseUrl],
  );

  const reset = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    dispatch({ type: "RESET" });
  }, []);

  useEffect(() => {
    return () => {
      if (abortRef.current) abortRef.current.abort();
    };
  }, []);

  return {
    phase: state.phase,
    stageStatus: state.stageStatus,
    log: state.log,
    result: state.result,
    error: state.error,
    errorStage: state.errorStage,
    loading: state.phase === "streaming" || state.phase === "legacy",
    showLog,
    run,
    reset,
  };
}
