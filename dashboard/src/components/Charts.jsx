import { useId } from 'react';

/* ---------------------------------------------------------------
   Graphiques SVG — sans dépendance, thème SAFIDIKO (violet/bleu)
   --------------------------------------------------------------- */

function niceMax(v) {
  const m = Math.max(v, 1);
  const pow = Math.pow(10, Math.floor(Math.log10(m)));
  const step = pow / 2;
  return Math.ceil((m * 1.12) / step) * step;
}

/* Courbe d'aire à deux séries (ex. scènes / choix) */
export function AreaChart({ data, primary = '#9555ff', secondary = '#31b7ff', legend }) {
  const id = useId().replace(/:/g, '');
  const W = 760, H = 232, padL = 30, padR = 14, padT = 20, padB = 28;
  const n = data.length;
  const a = data.map(d => d.a);
  const b = data.map(d => d.b ?? 0);
  const max = niceMax(Math.max(...a, ...b));
  const x = i => padL + (i * (W - padL - padR)) / (n - 1);
  const y = v => padT + (1 - v / max) * (H - padT - padB);
  const toLine = arr => arr.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
  const lineA = toLine(a);
  const areaA = `${lineA} L${x(n - 1).toFixed(1)} ${H - padB} L${x(0).toFixed(1)} ${H - padB} Z`;
  const lineB = toLine(b);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => ({ y: y(max * t), label: Math.round(max * t) }));
  const lastA = { x: x(n - 1), y: y(a[n - 1]) };

  return (
    <svg className="chart-svg" viewBox={`0 0 ${W} ${H}`} role="img"
         aria-label="Évolution éditoriale : scènes et choix ajoutés par semaine">
      <defs>
        <linearGradient id={`area-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={primary} stopOpacity="0.34" />
          <stop offset="1" stopColor={primary} stopOpacity="0" />
        </linearGradient>
      </defs>

      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={W - padR} y1={t.y} y2={t.y} stroke="rgba(255,255,255,0.055)" strokeWidth="1" />
          <text x={padL - 8} y={t.y + 3.5} textAnchor="end" className="chart-axis">{t.label}</text>
        </g>
      ))}

      <path d={areaA} fill={`url(#area-${id})`} />
      <path d={lineB} fill="none" stroke={secondary} strokeWidth="2" strokeDasharray="5 5"
            strokeOpacity="0.75" strokeLinecap="round" strokeLinejoin="round" />
      <path d={lineA} fill="none" stroke={primary} strokeWidth="2.6"
            strokeLinecap="round" strokeLinejoin="round" />

      {data.map((d, i) => (
        <text key={i} x={x(i)} y={H - 8} textAnchor="middle" className="chart-axis">{d.label}</text>
      ))}

      <circle cx={lastA.x} cy={lastA.y} r="5.5" fill="#0f1a2c" stroke={primary} strokeWidth="3" />

      {legend && (
        <g transform={`translate(${padL}, 8)`} className="chart-legend-svg">
          <rect x="0" y="-9" width="11" height="11" rx="2" fill={primary} />
          <text x="17" y="0" className="chart-legend-text">{legend[0]}</text>
          <rect x="92" y="-9" width="11" height="11" rx="2" fill={secondary} />
          <text x="109" y="0" className="chart-legend-text">{legend[1]}</text>
        </g>
      )}
    </svg>
  );
}

/* Anneau de répartition (statuts de contenu) */
export function Donut({ segments, centerValue, centerLabel }) {
  const R = 54, SW = 15, C = 2 * Math.PI * R;
  const total = segments.reduce((s, x) => s + x.value, 0) || 1;
  let acc = 0;
  return (
    <svg className="donut-svg" viewBox="0 0 140 140" role="img"
         aria-label={`Répartition : ${segments.map(s => `${s.label} ${s.value}`).join(', ')}`}>
      <g transform="rotate(-90 70 70)">
        <circle cx="70" cy="70" r={R} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={SW} />
        {segments.map((s, i) => {
          const len = (s.value / total) * C;
          const el = (
            <circle key={i} cx="70" cy="70" r={R} fill="none" stroke={s.color} strokeWidth={SW}
                    strokeDasharray={`${len.toFixed(1)} ${(C - len).toFixed(1)}`}
                    strokeDashoffset={(-acc).toFixed(1)} strokeLinecap="butt" />
          );
          acc += len;
          return el;
        })}
      </g>
      <text x="70" y="66" textAnchor="middle" className="donut-value">{centerValue}</text>
      <text x="70" y="84" textAnchor="middle" className="donut-label">{centerLabel}</text>
    </svg>
  );
}

/* Mini-courbe pour les cartes KPI */
export function Sparkline({ values, color = '#9555ff', className = '' }) {
  const id = useId().replace(/:/g, '');
  const W = 96, H = 30, p = 3;
  const mn = Math.min(...values), mx = Math.max(...values), r = (mx - mn) || 1;
  const x = i => p + (i * (W - 2 * p)) / (values.length - 1);
  const y = v => p + (1 - (v - mn) / r) * (H - 2 * p);
  const line = values.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(' ');
  const area = `${line} L${x(values.length - 1).toFixed(1)} ${H - p} L${x(0).toFixed(1)} ${H - p} Z`;
  return (
    <svg className={`spark ${className}`} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true">
      <defs>
        <linearGradient id={`sp-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={color} stopOpacity="0.3" />
          <stop offset="1" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#sp-${id})`} />
      <path d={line} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
