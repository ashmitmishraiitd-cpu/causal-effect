import { CheckCircle, XCircle, AlertTriangle, BarChart3, TrendingUp, Shield, Activity, Database, Beaker, Layers } from 'lucide-react';
import CausalChart from './CausalChart.jsx';

import { Component } from 'react';

const safe = (v, dflt = '') => v != null ? v : dflt;
const num = v => v == null ? 0 : Number(v);

class SectionBoundary extends Component {
  constructor(props) { super(props); this.state = { error: null }; }
  static getDerivedStateFromError(e) { return { error: e }; }
  componentDidCatch(e, info) { console.error(`[${this.props.name}]`, e, info); }
  render() {
    if (this.state.error) {
      return <div className="card p-6 text-center"><p className="text-red-400 text-sm font-mono">{this.props.name}: {this.state.error.message}</p></div>;
    }
    return this.props.children;
  }
}

export default function ResultsDashboard({ analysis, session, onBack }) {
  const s = analysis.summary || {};
  const { linear_regression, propensity_matching, doubly_robust, double_ml, causal_forest, refutations } = analysis;

  const methods = [
    { key: 'linear_regression', label: 'Linear Regression', data: linear_regression, color: '#e63946' },
    { key: 'propensity_matching', label: 'Propensity Score Matching', data: propensity_matching, color: '#d62828' },
    { key: 'doubly_robust', label: 'Doubly Robust (IPW)', data: doubly_robust, color: '#b71c1c' },
    { key: 'double_ml', label: 'Double ML', data: double_ml, color: '#f87171' },
    { key: 'causal_forest', label: 'Causal Forest', data: causal_forest, color: '#fca5a5' },
  ];

  const validMethods = methods.filter(m => m.data && !m.data.error && m.data.ate != null);

  const bestAte = validMethods.length > 0
    ? validMethods.reduce((a, b) => Math.abs(num(a.data.ate)) < Math.abs(num(b.data.ate)) ? a : b)
    : null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="card bg-gradient-to-r from-primary-950/80 via-red-950/40 to-gray-900 border-primary-800/50 animate-scale-in">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-emerald-500/20 rounded-xl flex items-center justify-center shrink-0 shadow-soft-dark">
            <CheckCircle className="w-6 h-6 text-emerald-400" />
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-gray-100">Analysis Complete</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {safe(s.treatment)} &rarr; {safe(s.outcome)} &middot; {safe((s.num_rows || 0).toLocaleString())} observations &middot; {(s.confounders || []).length} confounders
            </p>
          </div>
          <button onClick={onBack} className="btn-secondary text-xs py-2 px-3.5 shrink-0">Reconfigure</button>
        </div>
      </div>

      <SectionBoundary name="stat-cards">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 stagger-children">
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Database className="w-3.5 h-3.5 text-primary-400" />
              <p className="text-[11px] font-semibold text-primary-300 uppercase tracking-wider">Observations</p>
            </div>
            <p className="text-2xl font-bold text-gray-100">{safe((s.num_rows || 0).toLocaleString())}</p>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Beaker className="w-3.5 h-3.5 text-primary-400" />
              <p className="text-[11px] font-semibold text-primary-300 uppercase tracking-wider">Methods</p>
            </div>
            <p className="text-2xl font-bold text-gray-100">{validMethods.length}/5</p>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Layers className="w-3.5 h-3.5 text-primary-400" />
              <p className="text-[11px] font-semibold text-primary-300 uppercase tracking-wider">Confounders</p>
            </div>
            <p className="text-2xl font-bold text-gray-100">{(s.confounders || []).length}</p>
          </div>
          <div className="stat-card">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-3.5 h-3.5 text-primary-400" />
              <p className="text-[11px] font-semibold text-primary-300 uppercase tracking-wider">Missing</p>
            </div>
            <p className="text-2xl font-bold text-gray-100">{safe(s.missing_values)}</p>
          </div>
        </div>
      </SectionBoundary>

      <SectionBoundary name="ate-chart">
        <div className="card animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          <div className="flex items-center gap-2.5 pb-4 border-b border-white/10 mb-5">
            <div className="w-8 h-8 bg-primary-500/20 rounded-lg flex items-center justify-center">
              <TrendingUp className="w-4 h-4 text-primary-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-100 text-sm">Average Treatment Effect (ATE)</h3>
              <p className="text-xs text-gray-500">Comparison across all estimation methods</p>
            </div>
          </div>
          <CausalChart methods={validMethods} type="ate" />
        </div>
      </SectionBoundary>

      {causal_forest && !causal_forest.error && causal_forest.cate_distribution && (
        <SectionBoundary name="cate-chart">
          <div className="card animate-fade-in-up" style={{ animationDelay: '200ms' }}>
            <div className="flex items-center gap-2.5 pb-4 border-b border-white/10 mb-5">
              <div className="w-8 h-8 bg-amber-500/20 rounded-lg flex items-center justify-center">
                <BarChart3 className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-100 text-sm">CATE Distribution</h3>
                <p className="text-xs text-gray-500">Individual treatment effects across all units (Causal Forest)</p>
              </div>
            </div>
            <CausalChart type="cate" cateDist={causal_forest.cate_distribution} cateSamples={causal_forest.cate_samples} />
          </div>
        </SectionBoundary>
      )}

      <SectionBoundary name="refutation-tests">
        <div className="card animate-fade-in-up" style={{ animationDelay: '300ms' }}>
          <div className="flex items-center gap-2.5 pb-4 border-b border-white/10 mb-5">
            <div className="w-8 h-8 bg-emerald-500/20 rounded-lg flex items-center justify-center">
              <Shield className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h3 className="font-semibold text-gray-100 text-sm">Refutation Tests</h3>
              <p className="text-xs text-gray-500">Robustness checks for the estimated causal effect</p>
            </div>
          </div>
          {refutations && Object.keys(refutations).length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 stagger-children">
              {Object.entries(refutations).map(([name, data]) => {
                const hasEstimate = data && !data.error && data.original_estimate != null;
                const isEValue = data && data.e_value != null;
                return (
                <div key={name} className={`rounded-2xl p-5 border transition-all duration-300 hover:-translate-y-0.5
                  ${data.error
                    ? 'bg-orange-950/50 border-orange-800/40 hover:shadow-card-hover-dark'
                    : 'bg-white/[0.03] border-white/10 hover:shadow-card-hover-dark hover:border-white/20'}`}>
                  <div className="flex items-center gap-2 mb-3">
                    {data.error ? (
                      <AlertTriangle className="w-4 h-4 text-orange-400" />
                    ) : (
                      <CheckCircle className="w-4 h-4 text-emerald-400" />
                    )}
                    <span className="text-sm font-semibold text-gray-300">
                      {name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </span>
                  </div>
                  {data.error ? (
                    <p className="text-xs text-orange-400">{data.error}</p>
                  ) : isEValue ? (
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between items-center py-1.5">
                        <span className="text-gray-500 text-xs">E-value</span>
                        <span className="font-mono font-semibold text-gray-200">{Number(data.e_value || 0).toFixed(4)}</span>
                      </div>
                    </div>
                  ) : hasEstimate ? (
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between items-center py-1.5 border-b border-white/10">
                        <span className="text-gray-500 text-xs">Original</span>
                        <span className="font-mono font-semibold text-gray-200">{Number(data.original_estimate).toFixed(4)}</span>
                      </div>
                      <div className="flex justify-between items-center py-1.5 border-b border-white/10">
                        <span className="text-gray-500 text-xs">Refuted</span>
                        <span className="font-mono font-semibold text-gray-200">{Number(data.new_estimate).toFixed(4)}</span>
                      </div>
                      <div className="flex justify-between items-center py-1.5">
                        <span className="text-gray-500 text-xs">p-value</span>
                        <span className={`font-mono font-semibold ${data.p_value < 0.05 ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {Number(data.p_value).toFixed(4)}
                          <span className="text-[10px] ml-1 font-normal">{data.p_value < 0.05 ? '(pass)' : '(fail)'}</span>
                        </span>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500">Data unavailable</p>
                  )}
                </div>
                );
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-sm text-gray-500 bg-white/[0.02] rounded-2xl">
              <Shield className="w-8 h-8 mx-auto mb-2 text-gray-600" />
              No refutation tests available
            </div>
          )}
        </div>
      </SectionBoundary>

      <SectionBoundary name="detail-table">
        <div className="card animate-fade-in-up" style={{ animationDelay: '400ms' }}>
          <div className="flex items-center gap-2.5 pb-4 border-b border-white/10 mb-4">
            <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center">
              <Database className="w-4 h-4 text-gray-400" />
            </div>
            <h3 className="font-semibold text-gray-100 text-sm">Detailed Estimates</h3>
          </div>
          <div className="overflow-x-auto -mx-2">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10">
                  <th className="text-left py-3 px-4 font-semibold text-gray-500 text-xs uppercase tracking-wider">Method</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-500 text-xs uppercase tracking-wider">ATE</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-500 text-xs uppercase tracking-wider">CI Lower</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-500 text-xs uppercase tracking-wider">CI Upper</th>
                  <th className="text-center py-3 px-4 font-semibold text-gray-500 text-xs uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody>
                {methods.map(({ key, label, data, color }) => (
                  <tr key={key} className="border-b border-white/[0.03] hover:bg-primary-500/5 transition-colors duration-150">
                    <td className="py-3.5 px-4">
                      <div className="flex items-center gap-2.5">
                        <div className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: color }} />
                        <span className="font-medium text-gray-200 text-sm">{label}</span>
                      </div>
                    </td>
                    {data && !data.error && data.ate != null ? (
                      <>
                        <td className="text-right py-3.5 px-4 font-mono font-semibold text-gray-100 text-sm">{Number(data.ate).toFixed(5)}</td>
                        <td className="text-right py-3.5 px-4 font-mono text-gray-500 text-sm">
                          {data.ate_interval ? Number(data.ate_interval[0]).toFixed(5) : '\u2014'}
                        </td>
                        <td className="text-right py-3.5 px-4 font-mono text-gray-500 text-sm">
                          {data.ate_interval ? Number(data.ate_interval[1]).toFixed(5) : '\u2014'}
                        </td>
                        <td className="text-center py-3.5 px-4">
                          <span className="inline-flex items-center gap-1 tag bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                            <CheckCircle className="w-3 h-3" /> Success
                          </span>
                        </td>
                      </>
                    ) : (
                      <>
                        <td className="text-right py-3.5 px-4 font-mono text-gray-600">\u2014</td>
                        <td className="text-right py-3.5 px-4 font-mono text-gray-600">\u2014</td>
                        <td className="text-right py-3.5 px-4 font-mono text-gray-600">\u2014</td>
                        <td className="text-center py-3.5 px-4">
                          <span className="inline-flex items-center gap-1 tag bg-red-500/20 text-red-300 border-red-500/30">
                            <XCircle className="w-3 h-3" /> Error
                          </span>
                        </td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </SectionBoundary>

      {bestAte && (
        <SectionBoundary name="interpretation">
          <div className="bg-gradient-to-br from-primary-600 via-primary-700 to-primary-900 rounded-2xl p-6 sm:p-8 text-white shadow-glow-lg animate-fade-in-up" style={{ animationDelay: '500ms' }}>
            <div className="flex items-start gap-4">
              <div className="w-11 h-11 bg-white/15 backdrop-blur-sm rounded-xl flex items-center justify-center shrink-0">
                <TrendingUp className="w-5 h-5" />
              </div>
              <div>
                <p className="text-xs font-semibold text-primary-200 uppercase tracking-wider">Interpretation</p>
                <p className="mt-2 text-base sm:text-lg font-semibold leading-relaxed text-white/95">
                  The estimated Average Treatment Effect (ATE) across methods is centered around{' '}
                  <strong className="text-white text-xl">{Number(bestAte.data.ate).toFixed(4)}</strong>.
                  {bestAte.data.ate > 0
                    ? ' The treatment shows a positive effect on the outcome.'
                    : bestAte.data.ate < 0
                    ? ' The treatment shows a negative effect on the outcome.'
                    : ' No significant effect detected.'}
                </p>
                <p className="text-sm text-primary-200 mt-2 leading-relaxed">
                  This estimate is derived from {validMethods.length} causal inference methods, including propensity score matching and double machine learning.
                  {bestAte.data.ate_interval && (
                    <> The 95% confidence interval spans [{Number(bestAte.data.ate_interval[0]).toFixed(4)}, {Number(bestAte.data.ate_interval[1]).toFixed(4)}].</>
                  )}
                </p>
              </div>
            </div>
          </div>
        </SectionBoundary>
      )}
    </div>
  );
}
