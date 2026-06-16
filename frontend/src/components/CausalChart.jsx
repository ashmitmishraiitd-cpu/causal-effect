import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell } from 'recharts';

const num = v => v == null ? 0 : Number(v);
const round = (n, d = 4) => num(n).toFixed(d);

export default function CausalChart({ methods, type, cateDist, cateSamples }) {
  if (type === 'ate' && methods) {
    const data = methods.map(m => ({
      name: m.label.split(' ').slice(0, 2).join(' '),
      fullName: m.label,
      ATE: m.data.ate,
      ciLower: m.data.ate_interval ? m.data.ate_interval[0] : m.data.ate,
      ciUpper: m.data.ate_interval ? m.data.ate_interval[1] : m.data.ate,
      color: m.color,
    }));

    const CustomTooltip = ({ active, payload, label }) => {
      if (active && payload && payload.length) {
        const d = payload[0].payload;
        return (
          <div className="bg-gray-900/95 backdrop-blur-sm border border-white/10 rounded-2xl shadow-elevated-dark px-4 py-3 text-sm">
            <p className="font-semibold text-gray-100 mb-1.5 text-xs uppercase tracking-wide">{d.fullName}</p>
            <div className="space-y-1">
              <p className="text-gray-400 text-xs">ATE: <span className="font-mono font-semibold text-gray-100">{round(d.ATE)}</span></p>
              <p className="text-gray-400 text-xs">95% CI: [{round(d.ciLower)}, {round(d.ciUpper)}]</p>
            </div>
          </div>
        );
      }
      return null;
    };

    return (
      <ResponsiveContainer width="100%" height={320}>
        <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 16 }}>
          <CartesianGrid strokeDasharray="4 4" stroke="rgba(255,255,255,0.06)" vertical={false} />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6b7280', fontWeight: 500 }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: '#6b7280' }} axisLine={false} tickLine={false} />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
          <ReferenceLine y={0} stroke="rgba(255,255,255,0.15)" strokeWidth={1.5} />
          <Bar dataKey="ATE" radius={[8, 8, 0, 0]} barSize={44} animationDuration={800} animationBegin={200}>
            {data.map((entry, idx) => (
              <Cell key={idx} fill={entry.color} fillOpacity={0.85} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  }

  if (type === 'cate' && cateDist) {
    const histData = generateHistogram(cateSamples, 30);

    return (
      <div className="space-y-5">
        <div className="grid grid-cols-3 sm:grid-cols-7 gap-2 stagger-children">
          {[
            { label: 'Mean', value: cateDist.mean },
            { label: 'Std Dev', value: cateDist.std },
            { label: 'Min', value: cateDist.min },
            { label: 'P25', value: cateDist.p25 },
            { label: 'Median', value: cateDist.p50 },
            { label: 'P75', value: cateDist.p75 },
            { label: 'Max', value: cateDist.max },
          ].map(({ label, value }) => (
            <div key={label} className="bg-white/[0.03] rounded-xl p-2.5 text-center border border-white/10">
              <p className="text-[10px] text-gray-500 font-medium uppercase tracking-wider">{label}</p>
              <p className="text-sm font-mono font-bold text-gray-200 mt-0.5">{round(value)}</p>
            </div>
          ))}
        </div>

        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={histData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
            <XAxis dataKey="bin" tick={{ fontSize: 9, fill: '#6b7280' }} axisLine={{ stroke: 'rgba(255,255,255,0.08)' }} tickLine={false} interval={Math.floor(histData.length / 10)} />
            <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: 'rgba(17,17,23,0.95)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '12px',
                boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
                fontSize: '12px',
                color: '#e5e7eb',
              }}
            />
            <Bar dataKey="count" fill="#f87171" fillOpacity={0.6} radius={[4, 4, 0, 0]} animationDuration={800} animationBegin={400} />
          </BarChart>
        </ResponsiveContainer>
              <p className="text-xs text-gray-500 text-center font-medium">
                Distribution of individual treatment effects (CATE) across {(cateSamples || []).length.toLocaleString()} units
        </p>
      </div>
    );
  }

  return null;
}

function generateHistogram(samples, bins = 30) {
  if (!samples || samples.length === 0) return [];
  const min = Math.min(...samples);
  const max = Math.max(...samples);
  const binWidth = (max - min) / bins || 1;
  const counts = new Array(bins).fill(0);

  for (const val of samples) {
    const idx = Math.min(Math.floor((val - min) / binWidth), bins - 1);
    counts[idx]++;
  }

  const labels = [];
  for (let i = 0; i < bins; i++) {
    const lo = (min + i * binWidth).toFixed(2);
    const hi = (min + (i + 1) * binWidth).toFixed(2);
    labels.push({ bin: `${lo}\u2013${hi}`, count: counts[i] });
  }
  return labels;
}
