import { useState } from 'react';
import { Play, Settings2, RefreshCw, Info, AlertTriangle } from 'lucide-react';
import { runAnalysis } from '../api';

export default function ColumnMapper({ session, onAnalyze, setLoading, loading }) {
  const [treatment, setTreatment] = useState('');
  const [outcome, setOutcome] = useState('');
  const [confounders, setConfounders] = useState([]);
  const [error, setError] = useState(null);

  const { all_columns, numeric_columns, column_info, rows, columns } = session;

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!treatment || !outcome || confounders.length === 0) {
      setError('Please select treatment, outcome, and at least one confounder');
      return;
    }
    if (treatment === outcome) {
      setError('Treatment and outcome must be different columns');
      return;
    }
    if (confounders.includes(treatment) || confounders.includes(outcome)) {
      setError('Confounders cannot include treatment or outcome');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await runAnalysis(
        session.session_id,
        treatment,
        outcome,
        confounders.join(',')
      );
      onAnalyze(result.results);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleConfounderToggle = (col) => {
    setConfounders(prev =>
      prev.includes(col) ? prev.filter(c => c !== col) : [...prev, col]
    );
  };

  const columnsForOutcome = all_columns.filter(col => col !== treatment);

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="card-hover flex items-start gap-4 animate-scale-in">
        <div className="w-11 h-11 bg-gradient-to-br from-primary-600 to-primary-800 rounded-xl flex items-center justify-center shrink-0 shadow-soft-dark">
          <FileIcon />
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-100 truncate">{session.filename}</h3>
          <p className="text-sm text-gray-500">
            {rows.toLocaleString()} rows &middot; {columns} columns &middot; {numeric_columns.length} numeric
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card space-y-5 animate-fade-in-up" style={{ animationDelay: '80ms' }}>
            <div className="flex items-center gap-2.5 pb-2 border-b border-white/10">
              <div className="w-7 h-7 bg-primary-500/20 rounded-lg flex items-center justify-center">
                <Settings2 className="w-4 h-4 text-primary-400" />
              </div>
              <h3 className="font-semibold text-gray-100 text-sm">Variable Mapping</h3>
            </div>

            <div>
              <label className="label">
                Treatment Variable <span className="text-primary-400">*</span>
              </label>
              <select
                value={treatment}
                onChange={(e) => setTreatment(e.target.value)}
                className="input-field"
                required
              >
                <option value="">Select treatment column...</option>
                {all_columns.map(col => (
                  <option key={col} value={col}>
                    {col} {column_info[col]?.is_numeric ? '(numeric)' : '(categorical)'}
                  </option>
                ))}
              </select>
              {treatment && (
                <div className="flex gap-3 mt-2 text-xs text-gray-500">
                  <span>Unique: {column_info[treatment]?.unique}</span>
                  <span>Missing: {column_info[treatment]?.missing}</span>
                  <span>Type: {column_info[treatment]?.dtype}</span>
                </div>
              )}
            </div>

            <div>
              <label className="label">
                Outcome Variable <span className="text-primary-400">*</span>
              </label>
              <select
                value={outcome}
                onChange={(e) => setOutcome(e.target.value)}
                className="input-field"
                required
              >
                <option value="">Select outcome column...</option>
                {columnsForOutcome.map(col => (
                  <option key={col} value={col}>
                    {col} {column_info[col]?.is_numeric ? '(numeric)' : '(categorical)'}
                  </option>
                ))}
              </select>
              {outcome && (
                <div className="flex gap-3 mt-2 text-xs text-gray-500">
                  <span>Unique: {column_info[outcome]?.unique}</span>
                  <span>Missing: {column_info[outcome]?.missing}</span>
                  <span>Type: {column_info[outcome]?.dtype}</span>
                </div>
              )}
            </div>

            <div className="flex items-start gap-2 bg-primary-950/50 border border-primary-800/30 rounded-xl p-3">
              <Info className="w-4 h-4 text-primary-400 shrink-0 mt-0.5" />
              <p className="text-xs text-primary-300 leading-relaxed">
                Outcome should be a continuous numeric variable.
                {treatment && column_info[treatment]?.is_binary
                  ? ' Treatment is binary \u2014 all methods available.'
                  : treatment
                  ? ' Treatment is not binary (0/1). Propensity-based methods will be skipped.'
                  : ' Binary treatment (0/1) unlocks all estimation methods.'}
              </p>
            </div>
          </div>

          <div className="card space-y-4 animate-fade-in-up" style={{ animationDelay: '160ms' }}>
            <div className="flex items-center justify-between pb-2 border-b border-white/10">
              <div className="flex items-center gap-2.5">
                <div className="w-7 h-7 bg-amber-500/20 rounded-lg flex items-center justify-center">
                  <RefreshCw className="w-4 h-4 text-amber-400" />
                </div>
                <h3 className="font-semibold text-gray-100 text-sm">
                  Confounders <span className="text-primary-400">*</span>
                </h3>
              </div>
              <span className="text-xs font-medium text-gray-500 bg-white/5 px-2.5 py-1 rounded-lg">
                {confounders.length} selected
              </span>
            </div>

            <div className="max-h-72 overflow-y-auto space-y-1 pr-1 scrollbar-thin">
              {all_columns
                .filter(col => col !== treatment && col !== outcome)
                .map(col => {
                  const isSelected = confounders.includes(col);
                  const stats = column_info[col];
                  return (
                    <label
                      key={col}
                      className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl cursor-pointer transition-all duration-200
                        ${isSelected
                          ? 'bg-primary-500/15 border border-primary-500/30 shadow-soft-dark'
                          : 'hover:bg-white/[0.03] border border-transparent'}`}
                    >
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleConfounderToggle(col)}
                        className="w-4 h-4 rounded-md border-white/30 bg-white/10 text-primary-500 focus:ring-primary-500/40 focus:ring-offset-0"
                      />
                      <div className="flex-1 min-w-0">
                        <span className="text-sm font-medium text-gray-200">{col}</span>
                        <div className="flex gap-2 text-xs text-gray-500 mt-0.5">
                          <span>{stats?.dtype}</span>
                          <span>&middot;</span>
                          <span>{stats?.unique} unique</span>
                          {stats?.missing > 0 && (
                            <>
                              <span>&middot;</span>
                              <span className="text-amber-400">{stats.missing} missing</span>
                            </>
                          )}
                        </div>
                      </div>
                      {stats?.is_numeric && (
                        <span className="tag bg-blue-500/20 text-blue-300 border-blue-500/30">num</span>
                      )}
                    </label>
                  );
                })}
            </div>
          </div>
        </div>

        {error && (
          <div className="flex items-start gap-3 bg-red-950/80 border border-red-800/50 rounded-2xl p-4 animate-fade-in">
            <AlertTriangle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
            <p className="text-sm text-red-300">{error}</p>
          </div>
        )}

        <div className="flex justify-center pt-2 animate-fade-in-up" style={{ animationDelay: '240ms' }}>
          <button
            type="submit"
            disabled={loading || !treatment || !outcome || confounders.length === 0}
            className="btn-primary flex items-center gap-2.5 px-8 py-3 text-sm shadow-card-dark
              disabled:animate-none disabled:shadow-none"
          >
            {loading ? (
              <><RefreshCw className="w-4 h-4 animate-spin" /> Running Analysis...</>
            ) : (
              <><Play className="w-4 h-4" /> Run Causal Analysis</>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

function FileIcon() {
  return (
    <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
    </svg>
  );
}
