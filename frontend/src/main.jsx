import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error("GATI UI Runtime Exception:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#0a0e17',
          color: '#f8fafc',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'Inter, sans-serif',
          padding: '24px',
          textAlign: 'center'
        }}>
          <div style={{
            backgroundColor: '#131d2e',
            border: '1px solid #334866',
            borderRadius: '12px',
            padding: '32px',
            maxWidth: '680px',
            boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            textAlign: 'left',
          }}>
            <div style={{ fontSize: '24px', fontWeight: 'bold', color: '#38bdf8', marginBottom: '12px' }}>
              GATI Control Console
            </div>
            <div style={{ fontSize: '13px', color: '#ef4444', marginBottom: '14px', fontFamily: 'monospace', backgroundColor: 'rgba(239, 68, 68, 0.1)', padding: '10px', borderRadius: '6px' }}>
              {this.state.error ? this.state.error.toString() : 'Initializing telemetry...'}
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8', marginBottom: '20px' }}>
              If this error persists, click below to reset console state.
            </div>
            <button
              onClick={() => window.location.reload()}
              style={{
                backgroundColor: '#0284c7',
                color: '#ffffff',
                border: 'none',
                padding: '10px 24px',
                borderRadius: '6px',
                fontWeight: '600',
                cursor: 'pointer'
              }}
            >
              Reload Dashboard
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
)
