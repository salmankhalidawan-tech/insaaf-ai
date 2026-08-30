export default function Seal({ passed, size = 80, className = "" }) {
  const color = passed ? "hsl(var(--success))" : "hsl(var(--destructive))";
  const label = passed ? "INSAAF CERTIFIED" : "REVIEW REQUIRED";
  const pathId = `seal-arc-${passed ? "pass" : "fail"}`;

  return (
    <svg
      className={`shrink-0 animate-[stamp-in_0.4s_cubic-bezier(0.2,0.8,0.3,1.2)] ${className}`}
      width={size}
      height={size}
      viewBox="0 0 100 100"
      role="img"
      aria-label={label}
      style={{ transform: "rotate(-6deg)" }}
    >
      <defs>
        <path id={pathId} d="M 10,50 A 40,40 0 1,1 90,50" fill="none" />
      </defs>
      <circle cx="50" cy="50" r="46" fill="none" stroke={color} strokeWidth="2" />
      <circle
        cx="50"
        cy="50"
        r="38"
        fill="none"
        stroke={color}
        strokeWidth="0.8"
        strokeDasharray="2 3"
      />
      <text
        fill={color}
        fontSize="7"
        fontFamily="IBM Plex Mono, monospace"
        letterSpacing="1.5"
        fontWeight="600"
      >
        <textPath href={`#${pathId}`} startOffset="50%" textAnchor="middle">
          {label}
        </textPath>
      </text>
      {passed ? (
        <path
          d="M35 51 L45 61 L67 38"
          fill="none"
          stroke={color}
          strokeWidth="4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      ) : (
        <text
          x="50"
          y="58"
          fontSize="26"
          fontFamily="IBM Plex Mono, monospace"
          fill={color}
          textAnchor="middle"
        >!</text>
      )}
    </svg>
  );
}
