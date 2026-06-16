import { Component } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <div className="min-h-screen bg-[#0a0a0f] flex items-center justify-center p-8">
          <div className="max-w-md text-center space-y-4">
            <div className="w-16 h-16 mx-auto bg-red-500/20 rounded-2xl flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-xl font-bold text-gray-100">Something went wrong</h2>
            <p className="text-sm text-gray-500 font-mono bg-white/[0.03] rounded-xl p-4 border border-white/10">
              {this.state.error.message}
            </p>
            <button onClick={() => { this.setState({ error: null }); window.location.reload(); }}
              className="btn-primary inline-flex items-center gap-2 px-6 py-2.5 text-sm">
              <RefreshCw className="w-4 h-4" /> Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}