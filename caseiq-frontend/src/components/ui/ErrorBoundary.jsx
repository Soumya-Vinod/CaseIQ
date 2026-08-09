import { Component } from 'react';

class ErrorBoundary extends Component {
  state = { hasError: false, error: null };
  static getDerivedStateFromError(error) { return { hasError: true, error }; }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page-shell" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh' }}>
          <div className="gold-card" style={{ padding: '48px', maxWidth: '440px', textAlign: 'center' }}>
            <div style={{ fontSize: '3rem', marginBottom: '16px' }}>⚖️</div>
            <h2 className="serif-heading" style={{ fontSize: '1.5rem', marginBottom: '12px' }}>
              Something went wrong
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#555560', marginBottom: '24px' }}>
              {this.state.error?.message}
            </p>
            <button onClick={() => window.location.reload()} className="btn-gold" style={{ margin: '0 auto' }}>
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default ErrorBoundary;