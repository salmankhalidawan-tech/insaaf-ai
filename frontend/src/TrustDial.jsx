import { useState, useEffect } from "react";

export default function TrustDial({ score, size = 180, animate = true }) {
  const scale = size / 180;
  const strokeWidth = Math.max(4, Math.round(10 * scale));
  const radius = size / 2 - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  const center = size / 2;

  const fontSize = Math.round(42 * scale);
  const labelSize = Math.max(8, Math.round(10 * scale));

  const [displayScore, setDisplayScore] = useState(animate ? 0 : score);

  useEffect(() => {
    if (!animate) {
      setDisplayScore(score);
      return;
    }
    const raf = requestAnimationFrame(() => setDisplayScore(score));
    return () => cancelAnimationFrame(raf);
  }, [score, animate]);

  const progress = (displayScore / 100) * circumference;

  const color = score >= 70 ? "#059669" : score >= 40 ? "#D97706" : "#DC2626";
  const gradId = `trust-dial-grad-${size}`;

  return (
    <div
      className="relative inline-flex"
      style={{ width: size, height: size }}
    >
      <svg
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        className="-rotate-90"
      >
        <defs>
          <linearGradient id={gradId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={color} stopOpacity="0.7" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
        </defs>
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={`url(#${gradId})`}
          strokeWidth={strokeWidth}
          strokeDasharray={`${progress} ${circumference}`}
          strokeLinecap="round"
          style={{
            transition: animate
              ? "stroke-dasharray 0.7s cubic-bezier(0.4,0,0.2,1)"
              : "none",
          }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-display font-bold leading-none tabular-nums"
          style={{ color, fontSize: `${fontSize}px` }}
        >
          {displayScore}
        </span>
        <span
          className="font-mono uppercase tracking-widest text-muted-foreground mt-1"
          style={{ fontSize: `${labelSize}px` }}
        >
          Trust Score
        </span>
      </div>
    </div>
  );
}
