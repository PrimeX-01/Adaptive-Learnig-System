import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import AccessibilityPanel from './components/AccessibilityPanel';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
      <AccessibilityPanel />
    </ErrorBoundary>
  </React.StrictMode>
);
