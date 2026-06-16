import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle, Loader2, Table, ArrowRight } from 'lucide-react';
import { uploadCSV } from '../api';

export default function FileUpload({ onComplete }) {
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const onDrop = useCallback(async (acceptedFiles) => {
    const file = acceptedFiles[0];
    if (!file) return;
    if (!file.name.endsWith('.csv')) {
      setError('Only CSV files are supported');
      return;
    }
    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const data = await uploadCSV(file);
      setSuccess(`Loaded "${file.name}" - ${data.rows.toLocaleString()} rows, ${data.columns} columns`);
      setTimeout(() => onComplete(data), 800);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  }, [onComplete]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: uploading,
  });

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div className="text-center animate-fade-in-up">
        <h2 className="text-2xl font-bold text-gray-100 tracking-tight">Upload Your Dataset</h2>
        <p className="text-sm text-gray-500 mt-1.5 max-w-md mx-auto">
          CSV file containing treatment, outcome, and confounder variables for causal analysis
        </p>
      </div>

      <div
        {...getRootProps()}
        className={`relative border-2 border-dashed rounded-2xl p-12 text-center cursor-pointer transition-all duration-300
          ${isDragActive
            ? 'border-primary-400 bg-primary-500/10 scale-[1.02] shadow-glow'
            : 'border-white/20 hover:border-primary-300/50 hover:bg-white/[0.03] hover:shadow-card-hover-dark'}
          ${uploading ? 'pointer-events-none opacity-60' : ''}
          animate-scale-in backdrop-blur-sm`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-4">
          {uploading ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 bg-primary-500/20 rounded-2xl flex items-center justify-center animate-pulse">
                <Loader2 className="w-8 h-8 text-primary-400 animate-spin" />
              </div>
              <p className="text-sm font-medium text-gray-400">Uploading & parsing...</p>
            </div>
          ) : (
            <>
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center transition-all duration-300
                ${isDragActive ? 'bg-primary-500/30 scale-110 rotate-3' : 'bg-white/5'}`}>
                <Upload className={`w-8 h-8 transition-colors duration-300 ${isDragActive ? 'text-primary-300' : 'text-primary-400'}`} />
              </div>
              <div>
                <p className="text-base font-semibold text-gray-200">
                  {isDragActive ? 'Drop your CSV here' : 'Drag & drop your CSV file'}
                </p>
                <p className="text-sm text-gray-500 mt-0.5">or click to browse files</p>
              </div>
              <div className="inline-flex items-center gap-1.5 text-xs text-gray-500 bg-white/5 px-4 py-1.5 rounded-full border border-white/10">
                <FileSpreadsheet className="w-3.5 h-3.5" />
                .csv format only
              </div>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="flex items-start gap-3 bg-red-950/80 border border-red-800/50 rounded-2xl p-4 backdrop-blur-sm animate-fade-in">
          <AlertCircle className="w-5 h-5 text-red-400 shrink-0 mt-0.5" />
          <p className="text-sm text-red-300">{error}</p>
        </div>
      )}

      {success && (
        <div className="flex items-start gap-3 bg-emerald-950/80 border border-emerald-800/50 rounded-2xl p-4 animate-fade-in">
          <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-emerald-300 font-medium">{success}</p>
            <p className="text-xs text-emerald-400/80 mt-0.5">Proceeding to variable configuration...</p>
          </div>
          <ArrowRight className="w-5 h-5 text-emerald-400 animate-float" />
        </div>
      )}

      <div className="card-glass animate-fade-in-up" style={{ animationDelay: '150ms' }}>
        <div className="flex items-center gap-2 mb-4">
          <Table className="w-4 h-4 text-primary-400" />
          <h3 className="text-sm font-semibold text-gray-200">Expected CSV Format</h3>
        </div>
        <div className="text-sm text-gray-400 space-y-2 leading-relaxed">
          <p>Your CSV should contain columns for:</p>
          <div className="flex flex-wrap gap-2">
            <span className="tag bg-primary-500/20 text-primary-300 border border-primary-500/30">Treatment</span>
            <span className="tag bg-red-500/20 text-red-300 border border-red-500/30">Outcome</span>
            <span className="tag bg-amber-500/20 text-amber-300 border border-amber-500/30">Confounders</span>
          </div>
          <p className="text-gray-500 text-xs pt-1">
            Example: <code className="bg-white/10 px-2 py-0.5 rounded text-[11px] font-mono text-gray-300">age, treatment, outcome_score, income, education</code>
          </p>
        </div>
      </div>
    </div>
  );
}
