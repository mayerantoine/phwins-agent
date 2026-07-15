import { Bar, BarChart, Cell, LabelList, ResponsiveContainer, XAxis, YAxis } from 'recharts';
import { Chart } from '../api';
import styles from './ChartCard.module.css';

const HIGHLIGHT = '#c2410c';
const MUTED = '#d5cbb4';
const GROUP = '#b8b0a0';

export function ChartCard({ chart }: { chart: Chart }) {
  const data = chart.bars.map((b) => ({
    label: b.label,
    value: b.value_pct,
    fill: b.is_group ? GROUP : b.is_highlight ? HIGHLIGHT : MUTED,
  }));
  const height = Math.max(140, data.length * 44 + 60);

  return (
    <div className={styles.card}>
      <div className={styles.title}>{chart.title}</div>
      <div className={styles.subtitle}>{chart.subtitle}</div>
      <div className={styles.chart}>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 8, right: 48, bottom: 8, left: 8 }}
          >
            <XAxis
              type="number"
              domain={[0, 100]}
              ticks={[0, 25, 50, 75, 100]}
              tickFormatter={(v) => `${v}%`}
              stroke="var(--muted)"
              fontSize={12}
            />
            <YAxis
              type="category"
              dataKey="label"
              width={160}
              stroke="var(--ink)"
              fontSize={12}
              tickLine={false}
              axisLine={false}
            />
            <Bar dataKey="value" isAnimationActive={false} barSize={22}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.fill} />
              ))}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(v) => (typeof v === 'number' ? v.toFixed(1) : String(v ?? ''))}
                fontSize={12}
                fill="var(--ink)"
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      {chart.caption && <div className={styles.caption}>{chart.caption}</div>}
      <div className={styles.source}>
        PH WINS {chart.source.survey_year} · {chart.source.topic} → {chart.source.subtopic}
      </div>
    </div>
  );
}
