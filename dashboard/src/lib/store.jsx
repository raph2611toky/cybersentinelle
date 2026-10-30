import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { initialStories, initialResources, newGraph } from '../data/seed';

const AdminContext = createContext(null);
const STORAGE_KEY = 'safidiko.admin.demo.v1';
const AUTH_KEY = 'safidiko.auth.v1';
const uid = () => crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const initialState = { stories: initialStories, resources: initialResources };

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    if (Array.isArray(saved?.stories) && Array.isArray(saved?.resources)) return saved;
  } catch { /* stockage local indisponible */ }
  return initialState;
}

function loadAuth() {
  try {
    const saved = JSON.parse(localStorage.getItem(AUTH_KEY) || 'null');
    if (saved?.authed) return saved;
  } catch { /* stockage local indisponible */ }
  return { authed: false, user: null };
}

export function AdminProvider({ children }) {
  const [data, setData] = useState(loadState);
  const [auth, setAuth] = useState(loadAuth);
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(data)); } catch { /* espace indisponible */ }
  }, [data]);
  useEffect(() => {
    try { localStorage.setItem(AUTH_KEY, JSON.stringify(auth)); } catch { /* espace indisponible */ }
  }, [auth]);

  const login = (user = {}) => {
    const name = (user.name || user.email || 'Administrateur').trim();
    setAuth({ authed: true, user: { name, role: user.role || 'Studio SAFIDIKO' } });
  };
  const logout = () => setAuth({ authed: false, user: null });

  const addStory = ({ title, theme }) => {
    const story = { id: uid(), title: title.trim(), theme: theme.trim(), status: 'draft', language: 'FR / MG', updatedAt: new Date().toISOString(), graph: newGraph(title.trim()) };
    setData(prev => ({ ...prev, stories: [story, ...prev.stories] }));
    return story.id;
  };
  const updateStory = (id, patch) => setData(prev => ({ ...prev, stories: prev.stories.map(s => s.id === id ? { ...s, ...patch, updatedAt: new Date().toISOString() } : s) }));
  const removeStory = id => setData(prev => ({ ...prev, stories: prev.stories.filter(s => s.id !== id) }));
  const addResource = info => setData(prev => ({ ...prev, resources: [{ id: uid(), ...info, status: 'draft' }, ...prev.resources] }));
  const updateResource = (id, patch) => setData(prev => ({ ...prev, resources: prev.resources.map(r => r.id === id ? { ...r, ...patch } : r) }));
  const removeResource = id => setData(prev => ({ ...prev, resources: prev.resources.filter(r => r.id !== id) }));
  const resetDemo = () => setData(initialState);

  const value = useMemo(() => ({ ...data, auth, login, logout, addStory, updateStory, removeStory, addResource, updateResource, removeResource, resetDemo }), [data, auth]);
  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}

export function useAdmin() {
  const ctx = useContext(AdminContext);
  if (!ctx) throw new Error('useAdmin doit être utilisé dans AdminProvider');
  return ctx;
}
