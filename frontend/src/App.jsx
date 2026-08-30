import { useState, useCallback, useRef, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts";
import {
  Upload, FileText, X, ChevronRight, Download, Check,
  AlertCircle, RefreshCw, BarChart3, Info, Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { cn } from "@/lib/utils";
import Seal from "./Seal";
import TrustDial from "./TrustDial";
import ActivityLog from "./ActivityLog";
import CertificatePage from "./CertificatePage";
import useAuditRun from "./useAuditRun";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function App() {
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [protectedAttribute, setProtectedAttribute] = useState("");
  const [privilegedValue, setPrivilegedValue] = useState("");
  const [positiveOutcomeValue, setPositiveOutcomeValue] = useState("");
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const resultsRef = useRef(null);

  const audit = useAuditRun(API_BASE_URL);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragActive(false);
    const dropped = e.dataTransfer.files?.[0];
    if (dropped) setFile(dropped);
  }, []);

  useEffect(() => {
    if (audit.result) {
      setTimeout(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 80);
    }
  }, [audit.result]);

  if (window.location.pathname.startsWith("/certificate/")) {
    return <CertificatePage />;
  }

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

  const downloadReport = () => {
    if (!audit.result?.report_id) return;
    window.open(`${API_BASE_URL}/api/report/${audit.result.report_id}`, "_blank");
  };

  const shareCertificate = () => {
    if (!audit.result?.report_id) return;
    const url = `${window.location.origin}/certificate/${audit.result.report_id}`;
    navigator.clipboard.writeText(url).catch(() => {});
  };

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || !audit.result?.report_id) return;

    const question = chatInput.trim();
    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", text: question }]);
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE_URL}/api/audit/${audit.result.report_id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.answer || "Could not get an answer.");
      }
      setChatMessages((prev) => [...prev, { role: "assistant", text: data.answer }]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: err.message, isError: true },
      ]);
    } finally {
      setChatLoading(false);
    }
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
    <div className="min-h-screen flex flex-col bg-background relative isolate">
      <div
        className="fixed inset-0 -z-10 pointer-events-none"
        style={{
          background:
            "radial-gradient(1100px 480px at 88% -12%, hsl(var(--accent)) 0%, transparent 62%), radial-gradient(circle at 1px 1px, rgba(17,24,39,0.05) 1px, transparent 0)",
          backgroundSize: "auto, 24px 24px",
          WebkitMaskImage: "linear-gradient(180deg, #000 0%, transparent 72%)",
          maskImage: "linear-gradient(180deg, #000 0%, transparent 72%)",
        }}
      />

      {/* Top bar */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-xl border-b border-border">
        <div className="max-w-[1080px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <a href="/" className="flex items-center gap-2">
            <img
              src="/logo/lockup_horizontal.png"
              alt="Insaaf AI"
              className="h-7 w-auto"
            />
          </a>
          <span className="hidden sm:inline-block font-mono text-2xs uppercase tracking-widest text-muted-foreground">
            AI Accountability Auditor
          </span>
        </div>
      </nav>

      <main className="flex-1 w-full max-w-[1080px] mx-auto px-4 sm:px-6 pb-20">
        {/* Hero */}
        <section className="relative py-16 md:py-20">
          <div
            className="absolute top-[20%] -right-[10%] w-[380px] h-[380px] rounded-full pointer-events-none -z-10"
            style={{
              background: "hsl(var(--accent))",
              filter: "blur(80px)",
              opacity: 0.28,
            }}
          />
          <div className="grid md:grid-cols-[1fr_380px] gap-12 items-center">
            <div>
              <p className="inline-flex items-center gap-3 font-mono text-xs uppercase tracking-widest text-primary mb-4">
                <span className="w-6 h-0.5 bg-primary rounded-full" />
                Bias Audit Platform
              </p>
              <h1 className="font-display text-4xl md:text-5xl lg:text-[52px] font-bold leading-[1.1] tracking-tight text-foreground mb-5">
                Audit AI systems for <em className="text-primary not-italic">fairness</em> and
                accountability.
              </h1>
              <p className="text-lg text-muted-foreground max-w-[52ch] mb-7 leading-relaxed">
                Upload decision data from any AI system. Insaaf AI tests it against
                published fairness standards and issues a bilingual compliance
                report in minutes.
              </p>
              <Button size="lg" onClick={scrollToUpload} className="gap-2">
                Start an audit
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>

            <div className="hidden md:flex justify-center">
              <div className="relative w-full max-w-[380px] h-[260px]">
                <div className="absolute top-9 left-0 w-[300px] bg-card border border-border rounded-xl p-5 shadow-md opacity-90 [transform:perspective(900px)_rotateY(3deg)_rotateX(-1deg)_translateZ(-20px)] hover:[transform:perspective(900px)_rotateY(1deg)_rotateX(0)_translateZ(0)] transition-transform duration-500">
                  <div className="flex items-center gap-2 mb-3.5">
                    <BarChart3 className="w-3.5 h-3.5 text-muted-foreground" />
                    <span className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                      Feature Impact
                    </span>
                  </div>
                  <div className="space-y-2">
                    <PreviewBar label="income" width="85%" />
                    <PreviewBar label="city" width="60%" />
                    <PreviewBar label="gender" width="35%" warn />
                  </div>
                </div>
                <div className="absolute top-0 right-0 w-[300px] bg-card border border-border rounded-xl p-5 shadow-xl [transform:perspective(900px)_rotateY(-4deg)_rotateX(1.5deg)] hover:[transform:perspective(900px)_rotateY(0)_rotateX(0)_translateY(-4px)] transition-all duration-500 overflow-hidden">
                  <div className="absolute inset-0 -z-10 bg-gradient-to-br from-transparent via-white/55 to-transparent [transform:translateX(-60%)]" />
                  <div className="flex items-center justify-between mb-5">
                    <span className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                      Trust Report
                    </span>
                    <span className="font-mono text-[10px] font-semibold uppercase tracking-wide text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded">
                      Certified
                    </span>
                  </div>
                  <div className="flex items-center gap-5 mb-4">
                    <TrustDial score={82} size={80} />
                    <div className="flex-1 space-y-2">
                      <div className="flex justify-between items-baseline">
                        <span className="font-mono text-2xs uppercase text-muted-foreground">DIR</span>
                        <span className="font-mono font-semibold tabular-nums">0.87</span>
                      </div>
                      <div className="flex justify-between items-baseline">
                        <span className="font-mono text-2xs uppercase text-muted-foreground">EOD</span>
                        <span className="font-mono font-semibold tabular-nums">0.02</span>
                      </div>
                    </div>
                  </div>
                  <div className="font-mono text-2xs text-muted-foreground pt-3 border-t border-border">
                    Comparing: male vs. female
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Upload */}
        <section className="mb-12 scroll-mt-20" id="upload-section">
          <SectionHeader index="01" title="Upload dataset" desc="CSV with at least one protected attribute (gender, age, city) and one outcome column (approved / rejected)." />

          <Card
            className={cn(
              "overflow-hidden transition-all duration-200",
              dragActive && "border-primary ring-2 ring-primary/20"
            )}
            onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <CardContent className="p-0">
              <div className="p-8 md:p-10 text-center">
                {file ? (
                  <div className="flex items-center gap-4 max-w-md mx-auto bg-primary/5 border border-primary/20 rounded-lg p-4 mb-6 text-left">
                    <div className="shrink-0">
                      <FileText className="w-8 h-8 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-foreground truncate">{file.name}</p>
                      <p className="font-mono text-xs text-muted-foreground">{(file.size / 1024).toFixed(1)} KB</p>
                    </div>
                    <button
                      onClick={() => setFile(null)}
                      className="p-1.5 rounded-md text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                      title="Remove file"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 mb-6">
                    <div className="w-14 h-14 rounded-full bg-primary/10 flex items-center justify-center shadow-[0_0_0_8px_rgba(15,118,110,0.045)]">
                      <Upload className="w-7 h-7 text-primary" />
                    </div>
                    <p className="text-muted-foreground">Drop your CSV file here</p>
                    <p className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">or</p>
                  </div>
                )}

                <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
                  <label htmlFor="file-input">
                    <Button variant="outline" asChild>
                      <span>Choose file</span>
                    </Button>
                  </label>
                  <input
                    id="file-input"
                    type="file"
                    accept=".csv"
                    className="hidden"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                  />
                  <Button onClick={runAudit} disabled={!file || audit.loading} className="gap-2">
                    {audit.loading ? (
                      <>
                        <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        Analysing…
                      </>
                    ) : (
                      "Run audit"
                    )}
                  </Button>
                </div>
              </div>

              <div className="border-t border-border px-8 md:px-10 pb-6">
                <Accordion type="single" collapsible value={advancedOpen ? "advanced" : ""} onValueChange={(v) => setAdvancedOpen(v === "advanced")}>
                  <AccordionItem value="advanced" className="border-none">
                    <AccordionTrigger className="py-4 font-mono text-xs text-muted-foreground hover:text-foreground hover:no-underline">
                      Advanced options
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="grid sm:grid-cols-3 gap-4 pt-2">
                        <div className="space-y-1.5 text-left">
                          <label htmlFor="pa" className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                            Protected attribute
                          </label>
                          <Input
                            id="pa"
                            placeholder="auto-detect"
                            value={protectedAttribute}
                            onChange={(e) => setProtectedAttribute(e.target.value)}
                          />
                        </div>
                        <div className="space-y-1.5 text-left">
                          <label htmlFor="pv" className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                            Privileged value
                          </label>
                          <Input
                            id="pv"
                            placeholder="e.g. male or Lahore,Karachi"
                            value={privilegedValue}
                            onChange={(e) => setPrivilegedValue(e.target.value)}
                          />
                        </div>
                        <div className="space-y-1.5 text-left">
                          <label htmlFor="pov" className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                            Positive outcome value
                          </label>
                          <Input
                            id="pov"
                            placeholder="e.g. approved"
                            value={positiveOutcomeValue}
                            onChange={(e) => setPositiveOutcomeValue(e.target.value)}
                          />
                        </div>
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </div>
            </CardContent>
          </Card>

          {audit.error && (
            <div className="flex items-center gap-3 mt-4 p-4 rounded-lg bg-destructive/10 border border-destructive/20 text-destructive">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <div className="flex-1 flex flex-col gap-0.5">
                {audit.errorStage && (
                  <span className="font-mono text-2xs uppercase tracking-wide opacity-70">
                    Failed at: {audit.errorStage}
                  </span>
                )}
                <span className="text-sm">{audit.error}</span>
              </div>
              <Button variant="outline" size="sm" onClick={retryAudit} className="gap-2 shrink-0">
                <RefreshCw className="w-3.5 h-3.5" />
                Retry
              </Button>
            </div>
          )}
        </section>

        {/* Activity log */}
        {audit.showLog && (
          <section className="mb-12">
            <ActivityLog
              stageStatus={audit.stageStatus}
              log={audit.log}
              phase={audit.phase}
              error={audit.error}
              onRetry={retryAudit}
            />
          </section>
        )}

        {/* Results */}
        {result && (
          <div ref={resultsRef} className="space-y-12 animate-in fade-in slide-in-from-bottom-3 duration-500">
            {/* Verdict */}
            <section>
              <SectionHeader index="02" title="Audit verdict" />
              <Card className="p-1">
                <CardContent className="p-6 md:p-9">
                  <div className="grid md:grid-cols-[180px_1fr] gap-8 items-center">
                    <div className="flex justify-center md:justify-start">
                      <TrustDial score={result.report.trust_score} />
                    </div>
                    <div>
                      <Badge
                        variant={result.report.certified ? "default" : "destructive"}
                        className="mb-3 gap-1.5 font-mono text-xs uppercase tracking-wide"
                      >
                        {result.report.certified ? (
                          <Check className="w-3.5 h-3.5" />
                        ) : (
                          <AlertCircle className="w-3.5 h-3.5" />
                        )}
                        {result.report.certified ? "Certified fair" : "Bias flagged"}
                      </Badge>
                      <h3 className="font-display text-xl md:text-2xl font-semibold text-foreground mb-2">
                        {result.bias_detection.bias_detected
                          ? "This system shows measurable bias."
                          : "This system passed the fairness checks tested."}
                      </h3>
                      <p className="text-sm text-muted-foreground leading-relaxed">
                        Audited against <strong className="text-foreground">{result.config_used.protected_attribute}</strong> using{" "}
                        <strong className="text-foreground">{result.config_used.outcome_column}</strong> as the outcome,
                        across {result.intake.row_count.toLocaleString()} records.
                      </p>
                      {result.report.group_comparison && (
                        <p className="mt-3 font-mono text-xs text-muted-foreground tracking-wide">
                          {result.report.group_comparison.en}
                        </p>
                      )}
                      {autoDetectParts.length > 0 && (
                        <p className="inline-flex items-center gap-1.5 mt-3 font-mono text-2xs text-amber-700 bg-amber-50 rounded px-2.5 py-1">
                          <Info className="w-3 h-3" />
                          Auto-detected: {autoDetectParts.join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </section>

            {/* Metrics */}
            <section>
              <SectionHeader index="03" title="Fairness metrics" />
              <div className="grid md:grid-cols-2 gap-4 mb-4">
                <MetricCard
                  label="Disparate Impact Ratio"
                  pass={dirScore?.passes_80_percent_rule}
                  value={dirScore?.score}
                  detail={
                    <>
                      {dirScore?.passes_80_percent_rule ? "Passes" : "Fails"} the 80% rule. Privileged{" "}
                      {(dirScore?.privileged_positive_rate * 100).toFixed(1)}% vs. unprivileged{" "}
                      {(dirScore?.unprivileged_positive_rate * 100).toFixed(1)}%.
                    </>
                  }
                />
                <MetricCard
                  label="Equal Opportunity Difference"
                  pass={eodScore?.within_acceptable_range}
                  value={eodScore?.score}
                  detail={
                    eodScore ? (
                      <>
                        {eodScore.within_acceptable_range ? "Within" : "Outside"} the accepted ±0.1 range between groups.
                      </>
                    ) : (
                      <span className="italic text-muted-foreground">Requires a ground-truth outcome column.</span>
                    )
                  }
                />
              </div>

              {features.length > 0 && (
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="font-mono text-2xs uppercase tracking-wide text-muted-foreground font-medium">
                      Top Contributing Features
                    </CardTitle>
                    <CardDescription>{result.explainability.note}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ResponsiveContainer width="100%" height={240}>
                      <BarChart data={features} layout="vertical" margin={{ left: 10, right: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="hsl(var(--border))" />
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
                            background: "hsl(var(--card))",
                            border: "1px solid hsl(var(--border))",
                            borderRadius: "var(--radius)",
                            fontFamily: "IBM Plex Mono",
                            fontSize: 12,
                          }}
                        />
                        <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                          {features.map((f, i) => (
                            <Cell
                              key={i}
                              fill={
                                f.feature === result.config_used.protected_attribute
                                  ? "#DC2626"
                                  : "hsl(var(--primary))"
                              }
                            />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </CardContent>
                </Card>
              )}
            </section>

            {/* Bilingual Report */}
            <section>
              <SectionHeader index="04" title="Compliance report" />
              <div className="grid md:grid-cols-2 gap-4 mb-6">
                <Card className="bg-gradient-to-b from-card to-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-mono text-2xs uppercase tracking-wide text-primary font-medium">
                      English
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm leading-7 whitespace-pre-line text-foreground">
                      {result.report.summary_english}
                    </p>
                  </CardContent>
                </Card>
                <Card className="border-r-4 border-r-primary/20 bg-gradient-to-l from-primary/5 to-card">
                  <CardHeader className="pb-2">
                    <CardTitle className="font-urdu text-2xs uppercase tracking-wide text-primary font-medium">
                      اردو
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="font-urdu text-lg leading-[2.2] text-foreground whitespace-pre-line text-right" dir="rtl">
                      {result.report.summary_urdu}
                    </p>
                  </CardContent>
                </Card>
              </div>

              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-6 border-t border-border">
                <Seal passed={result.report.certified} size={80} />
                <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
                  {result.report.certified && (
                    <Button variant="outline" onClick={shareCertificate} className="gap-2">
                      <Check className="w-4 h-4" />
                      Share certificate
                    </Button>
                  )}
                  <Button onClick={downloadReport} className="gap-2">
                    <Download className="w-4 h-4" />
                    Download PDF report
                  </Button>
                </div>
              </div>
            </section>

            {/* Mitigation */}
            {result.mitigation && result.mitigation.mitigation_applied && (
              <section>
                <SectionHeader index="05" title="Suggested fix" />
                <Card>
                  <CardContent className="p-6 md:p-8">
                    <div className="flex items-center justify-center gap-6 md:gap-8 mb-6 pb-6 border-b border-border">
                      <ScoreItem label="Original score" value={result.mitigation.original_trust_score} />
                      <span className="text-3xl text-primary font-light">→</span>
                      <ScoreItem label="Projected score" value={result.mitigation.projected_trust_score} projected />
                    </div>

                    <div className="flex justify-center gap-8 md:gap-10 mb-6">
                      <MiniMetric label="Original DIR" value={result.mitigation.original_dir} />
                      <MiniMetric label="Projected DIR" value={result.mitigation.projected_dir} projected />
                    </div>

                    <p className="text-muted-foreground text-center max-w-2xl mx-auto mb-6 leading-relaxed">
                      {result.mitigation.explanation}
                    </p>

                    <div className="rounded-lg border border-border overflow-hidden">
                      <div className="flex items-center justify-between px-4 py-3 bg-primary/5 border-b border-border">
                        <span className="font-mono text-xs uppercase tracking-wide text-muted-foreground">
                          Python snippet
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => navigator.clipboard.writeText(result.mitigation.code_snippet)}
                          className="gap-2"
                        >
                          <FileText className="w-3.5 h-3.5" />
                          Copy code
                        </Button>
                      </div>
                      <pre className="p-4 overflow-x-auto font-mono text-xs leading-relaxed text-foreground bg-secondary/50">
                        <code>{result.mitigation.code_snippet}</code>
                      </pre>
                    </div>
                  </CardContent>
                </Card>
              </section>
            )}

            {/* Chat */}
            {result.report_id && (
              <section>
                <SectionHeader index="06" title="Ask about this report" />
                <Card className="overflow-hidden">
                  <CardContent className="p-0">
                    <div className="max-h-[360px] overflow-y-auto p-5 flex flex-col gap-4">
                      {chatMessages.length === 0 && (
                        <p className="text-center text-muted-foreground italic my-6">
                          Ask a question grounded in this audit’s metrics, e.g. “What is the
                          Disparate Impact Ratio?” or “Which feature contributed most?”
                        </p>
                      )}
                      {chatMessages.map((msg, i) => (
                        <div
                          key={i}
                          className={cn(
                            "flex flex-col gap-1 max-w-[80%]",
                            msg.role === "user" ? "self-end items-end" : "self-start items-start"
                          )}
                        >
                          <span className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                            {msg.role === "user" ? "You" : "Insaaf AI"}
                          </span>
                          <p
                            className={cn(
                              "m-0 px-4 py-3 rounded-xl text-sm leading-relaxed whitespace-pre-wrap",
                              msg.role === "user"
                                ? "bg-primary text-primary-foreground"
                                : "bg-secondary border border-border text-foreground",
                              msg.isError && "text-destructive bg-destructive/10 border-destructive/20"
                            )}
                          >
                            {msg.text}
                          </p>
                        </div>
                      ))}
                      {chatLoading && (
                        <div className="flex flex-col gap-1 self-start items-start max-w-[80%]">
                          <span className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
                            Insaaf AI
                          </span>
                          <span className="inline-flex items-center gap-2 px-4 py-3 rounded-xl bg-secondary border border-border text-sm text-muted-foreground">
                            <span className="w-3.5 h-3.5 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                            Thinking…
                          </span>
                        </div>
                      )}
                    </div>
                    <form onSubmit={askQuestion} className="flex gap-3 p-4 border-t border-border bg-card">
                      <Input
                        className="flex-1"
                        placeholder="Ask a question about this audit…"
                        value={chatInput}
                        onChange={(e) => setChatInput(e.target.value)}
                        disabled={chatLoading}
                      />
                      <Button type="submit" disabled={chatLoading || !chatInput.trim()} className="gap-2">
                        <Send className="w-4 h-4" />
                        Ask
                      </Button>
                    </form>
                  </CardContent>
                </Card>
              </section>
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-border bg-gradient-to-b from-transparent to-muted/30">
        <div className="max-w-[1080px] mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted-foreground font-mono">
          <span>Insaaf AI</span>
          <span>Alibaba Cloud AI Hackathon Pakistan 2026</span>
        </div>
      </footer>
    </div>
  );
}

function SectionHeader({ index, title, desc }) {
  return (
    <div className="mb-5">
      <div className="flex items-center gap-3 mb-3">
        <span className="font-mono text-2xs font-semibold uppercase tracking-widest text-primary bg-primary/10 border border-primary/20 rounded-full px-2.5 py-0.5 tabular-nums">
          {index}
        </span>
        <span className="flex-1 h-px bg-gradient-to-r from-border to-transparent" aria-hidden="true" />
      </div>
      <h2 className="font-display text-2xl font-semibold text-foreground tracking-tight">{title}</h2>
      {desc && <p className="text-sm text-muted-foreground mt-1 max-w-[60ch]">{desc}</p>}
    </div>
  );
}

function PreviewBar({ label, width, warn }) {
  return (
    <div className="flex items-center gap-2">
      <span className="font-mono text-[10px] text-muted-foreground w-[42px] text-right">{label}</span>
      <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", warn ? "bg-destructive" : "bg-primary")}
          style={{ width }}
        />
      </div>
    </div>
  );
}

function MetricCard({ label, pass, value, detail }) {
  return (
    <Card className="relative overflow-hidden">
      <div
        className={cn(
          "absolute left-0 top-0 bottom-0 w-1",
          pass ? "bg-emerald-600" : "bg-destructive"
        )}
      />
      <CardContent className="p-6">
        <h4 className="font-mono text-2xs uppercase tracking-wide text-muted-foreground mb-2">
          {label}
        </h4>
        {value !== undefined && value !== null ? (
          <p
            className={cn(
              "font-display text-3xl font-bold tracking-tight tabular-nums mb-2",
              pass ? "text-emerald-600" : "text-destructive"
            )}
          >
            {value}
          </p>
        ) : null}
        <p className="text-sm text-muted-foreground leading-relaxed">{detail}</p>
      </CardContent>
    </Card>
  );
}

function ScoreItem({ label, value, projected }) {
  return (
    <div className="flex flex-col items-center gap-1">
      <span
        className={cn(
          "font-display text-5xl font-bold leading-none",
          projected ? "text-emerald-600" : "text-foreground"
        )}
      >
        {value}
      </span>
      <span className="font-mono text-2xs uppercase tracking-wide text-muted-foreground">
        {label}
      </span>
    </div>
  );
}

function MiniMetric({ label, value, projected }) {
  return (
    <div className="text-center">
      <span className="block font-mono text-2xs uppercase tracking-wide text-muted-foreground mb-1">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-lg font-semibold tabular-nums",
          projected ? "text-emerald-600" : "text-foreground"
        )}
      >
        {value}
      </span>
    </div>
  );
}

export default App;
