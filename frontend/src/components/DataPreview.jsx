import { Table2 } from 'lucide-react';

export default function DataPreview({ sample, columns }) {
  if (!sample || sample.length === 0) return null;

  const cols = columns || Object.keys(sample[0]);

  return (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2.5 pb-4 border-b border-surface-200 mb-4">
        <div className="w-8 h-8 bg-primary-100 rounded-lg flex items-center justify-center">
          <Table2 className="w-4 h-4 text-primary-700" />
        </div>
        <div>
          <h3 className="font-semibold text-primary-900 text-sm">Data Preview</h3>
          <p className="text-xs text-surface-300">First {sample.length} rows</p>
        </div>
      </div>
      <div className="overflow-x-auto -mx-2">
        <table className="data-table">
          <thead>
            <tr>
              {cols.map(col => (
                <th key={col}>{col}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sample.map((row, i) => (
              <tr key={i}>
                {cols.map(col => (
                  <td key={col}>
                    {row[col] !== null && row[col] !== undefined
                      ? typeof row[col] === 'number'
                        ? Number(row[col].toFixed(4))
                        : String(row[col])
                      : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
