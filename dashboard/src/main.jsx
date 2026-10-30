import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AdminProvider } from './lib/store';
import App from './App';
import '@xyflow/react/dist/style.css';
import './styles/app.css';

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <AdminProvider><App /></AdminProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
