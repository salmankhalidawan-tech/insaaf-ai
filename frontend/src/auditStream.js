export const AUDIT_STAGES = [
  { key: "upload",         label: "Parsing the uploaded CSV" },
  { key: "intake",         label: "Validating the dataset" },
  { key: "bias_detection", label: "Testing for bias" },
  { key: "explainability", label: "Explaining the results" },
  { key: "translation",    label: "Preparing the Urdu report" },
  { key: "reporting",      label: "Calculating the trust score" },
  { key: "pdf_generation", label: "Generating the PDF report" },
];

export class StreamUnsupportedError extends Error {
  constructor() {
    super("Streaming not supported");
    this.name = "StreamUnsupportedError";
  }
}

function toFormData(file, fields) {
  const fd = new FormData();
  fd.append("file", file);
  if (fields.protectedAttribute) fd.append("protected_attribute", fields.protectedAttribute);
  if (fields.privilegedValue) fd.append("privileged_value", fields.privilegedValue);
  if (fields.positiveOutcomeValue) fd.append("positive_outcome_value", fields.positiveOutcomeValue);
  return fd;
}

function findFrameEnd(buf) {
  const a = buf.indexOf("\n\n");
  const b = buf.indexOf("\r\n\r\n");
  if (b !== -1 && (a === -1 || b < a)) return { index: b, length: 4 };
  if (a !== -1) return { index: a, length: 2 };
  return -1;
}

function parseFrame(raw) {
  const dataLines = [];
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.startsWith(":")) continue;
    if (!line.startsWith("data:")) continue;
    dataLines.push(line.slice(5).replace(/^ /, ""));
  }
  if (!dataLines.length) return null;
  try { return JSON.parse(dataLines.join("\n")); }
  catch { return null; }
}

export async function streamAudit({ baseUrl, file, fields, onEvent, signal }) {
  const res = await fetch(`${baseUrl}/api/audit-stream`, {
    method: "POST",
    body: toFormData(file, fields),
    signal,
  });

  if (res.status === 404 || res.status === 405) throw new StreamUnsupportedError();
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail?.error || detail?.detail || `Audit failed (${res.status}).`);
  }

  const ct = res.headers.get("content-type") || "";
  if (!ct.includes("text/event-stream")) throw new StreamUnsupportedError();
  if (!res.body) throw new StreamUnsupportedError();

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let finalResult = null;
  let sawEvent = false;

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) { buffer += decoder.decode(); }
      else { buffer += decoder.decode(value, { stream: true }); }

      let sep;
      while ((sep = findFrameEnd(buffer)) !== -1) {
        const raw = buffer.slice(0, sep.index);
        buffer = buffer.slice(sep.index + sep.length);
        const payload = parseFrame(raw);
        if (!payload) continue;
        sawEvent = true;
        onEvent(payload);
        if (payload.stage === "complete") finalResult = payload.result;
        if (payload.status === "error") {
          const err = new Error(payload.label || "Audit failed.");
          err.stage = payload.stage;
          err.sawEvent = true;
          throw err;
        }
      }
      if (done) break;
    }
  } finally {
    reader.cancel().catch(() => {});
  }

  if (!finalResult) {
    const err = new Error("The audit stream ended before results arrived.");
    err.sawEvent = sawEvent;
    throw err;
  }
  return finalResult;
}

export async function runAuditPlain({ baseUrl, file, fields, signal }) {
  const res = await fetch(`${baseUrl}/api/audit`, {
    method: "POST",
    body: toFormData(file, fields),
    signal,
  });
  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.detail?.error || data.detail || "Audit failed.");
  }
  return data;
}
