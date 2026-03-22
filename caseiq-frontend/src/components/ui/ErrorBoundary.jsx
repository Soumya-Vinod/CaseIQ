import { Component } from 'react';

class ErrorBoundary extends Component {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#D5DCF9] to-[#8EDCE6]">
          <div className="bg-white rounded-3xl shadow-2xl p-12 max-w-md text-center space-y-6">
            <div className="text-6xl">⚖️</div>
            <h1 className="text-2xl font-bold text-[#443627]">Something went wrong</h1>
            <p className="text-[#725E54] text-sm">{this.state.error?.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="bg-[#443627] text-white px-8 py-3 rounded-xl hover:bg-[#725E54] transition"
            >
              Reload App
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;