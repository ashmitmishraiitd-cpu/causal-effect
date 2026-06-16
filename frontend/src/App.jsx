import { useState } from 'react';
import { FlaskConical, ArrowLeft, Upload, BarChart3, Activity } from 'lucide-react';
import FileUpload from './components/FileUpload.jsx';
import ColumnMapper from './components/ColumnMapper.jsx';
import ResultsDashboard from './components/ResultsDashboard.jsx';
import LavaGlass from './components/LavaGlass.jsx';

export default function App() {
  const [step, setStep] = useState('upload');
  const [session, setSession] = useState(null);
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUploadComplete = (data) => {
    setSession(data);
    setStep('configure');
  };

  const handleAnalysisComplete = (results) => {
    setAnalysis(results);
    setStep('results');
  };

  const handleReset = () => {
    setSession(null);
    setAnalysis(null);
    setStep('upload');
  };

  const steps = [
    { key: 'upload', label: 'Upload', icon: Upload },
    { key: 'configure', label: 'Configure', icon: BarChart3 },
    { key: 'results', label: 'Results', icon: Activity },
  ];

  const currentIdx = steps.findIndex(s => s.key === step);

  return (
    <div className="min-h-screen relative">
      <LavaGlass />
      <header className="bg-black/40 backdrop-blur-xl border-b border-white/10 sticky top-0 z-20 animate-fade-in-down">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-primary-600 to-primary-800 rounded-xl flex items-center justify-center shadow-soft-dark">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">CausalInsight</h1>
              <p className="text-[11px] text-gray-500 font-medium -mt-0.5">Causal Inference Platform</p>
            </div>
          </div>
          {step !== 'upload' && (
            <button onClick={handleReset} className="btn-secondary flex items-center gap-1.5 text-xs py-2 px-3.5">
              <ArrowLeft className="w-3.5 h-3.5" /> New Analysis
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 animate-fade-in relative z-10">
        <div className="flex items-center justify-center gap-0 mb-10">
          {steps.map((s, i) => {
            const StepIcon = s.icon;
            const isActive = i === currentIdx;
            const isDone = i < currentIdx;
            return (
              <div key={s.key} className="flex items-center">
                {i > 0 && (
                  <div className={`w-10 sm:w-16 h-px transition-all duration-500 ${isDone || isActive ? 'bg-primary-400' : 'bg-white/10'}`} />
                )}
                <div className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-xl transition-all duration-500
                  ${isActive
                    ? 'bg-primary-600 text-white shadow-glow scale-105'
                    : isDone
                      ? 'bg-primary-500/20 text-primary-300 border border-primary-500/30'
                      : 'bg-white/5 text-gray-500 border border-white/10'}`}>
                  <StepIcon className="w-4 h-4" />
                  <span className={`text-xs font-semibold hidden sm:inline ${isActive ? 'text-white' : ''}`}>{s.label}</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="animate-fade-in-up" key={step}>
          {step === 'upload' && <FileUpload onComplete={handleUploadComplete} />}
          {step === 'configure' && session && (
            <ColumnMapper session={session} onAnalyze={handleAnalysisComplete} setLoading={setLoading} loading={loading} />
          )}
          {step === 'results' && analysis && (
            <ResultsDashboard analysis={analysis} session={session} onBack={() => setStep('configure')} />
          )}
        </div>
      </main>

      <footer className="text-center py-6 text-[11px] text-gray-500 font-medium tracking-wide relative z-10">
        CausalInsight &middot; DoWhy + EconML &middot; FastAPI + React
      </footer>
    </div>
  );
}
