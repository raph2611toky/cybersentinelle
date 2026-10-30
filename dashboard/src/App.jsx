import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Shell from './components/Shell';
import Login from './pages/Login';
import Overview from './pages/Overview';
import Tantara from './pages/Tantara';
import StoryTree from './pages/StoryTree';
import Media from './pages/Media';
import Voice from './pages/Voice';
import Resources from './pages/Resources';
import Publication from './pages/Publication';
import SettingsPage from './pages/Settings';
import { useAdmin } from './lib/store';

function RequireAuth({ children }) {
  const { auth } = useAdmin();
  const location = useLocation();
  if (auth.loading) return <div className="loading-screen">Vérification de la session administrateur…</div>;
  return auth.authed ? children : <Navigate to="/login" replace state={{ from: location }} />;
}

export default function App() {
  return <Routes>
    <Route path="/login" element={<Login />} />
    <Route element={<RequireAuth><Shell /></RequireAuth>}>
      <Route index element={<Overview />} />
      <Route path="tantara" element={<Tantara />} />
      <Route path="arbre" element={<StoryTree />} />
      <Route path="medias" element={<Media />} />
      <Route path="voix" element={<Voice />} />
      <Route path="ressources" element={<Resources />} />
      <Route path="publication" element={<Publication />} />
      <Route path="parametres" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  </Routes>;
}
