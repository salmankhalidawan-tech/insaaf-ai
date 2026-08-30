import { useState, useEffect } from "react";

export default function TrustDial({ score, size = 180, animate = true }) {
  const scale = size / 180;
  const strokeWidth = Math.max(4, Math.round(10 * scale));
  const radius = (size / 2) - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  const fontSize = Math.round(42 * scale);
  const labelSize = Math.max(8, Math.round(10 * scale));

  const [displayScore, setDisplayScore] = useState(animate ? 0 : score);

  useEffect(() => {
    if (!animate) { setDisplayScore(score); return; }
    const raf = requestAnimationFrame(() => setDisplayScore(score));
    return () => cancelAnimationFrame(raf);
  }, [score, animate]);

  const progress = (displayScore / 100) * circumference;

  const color =
    score >= 70 ? "var(--success)" :
    score >= 40 ? "var(--warning)"  :
                  "var(--danger)";

  const gradId = `trust-dial-grad-${size}`;

  return (
    <div className="trust-dial" style={{ width: size, height: size }}>
      <svg viewBox={`0 0 ${size} ${size}`} width={size} height={size}>
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.7" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
        </defs>
        <circle
          cx={center} cy={center} r={radius}
          fill="none" stroke="var(--border)" strokeWidth={strokeWidth}
        />
        <circle
          cx={center} cy={center} r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeDasharray={`${progress} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: animate ? "stroke-dasharray 0.7s cubic-bezier(0.4,0,0.2,1)" : "none" }}
        />
      </svg>
      <div className="trust-dial-value">
        <span className="trust-dial-number" style={{ color, fontSize: `${fontSize}px` }}>{displayScore}</span>
        <span className="trust-dial-label" style={{ fontSize: `${labelSize}px` }}>Trust Score</span>
      </div>
    </div>
  );
}
