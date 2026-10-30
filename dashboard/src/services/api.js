import axios from 'axios';

// En local, Vite relaie /api vers Django : même origine, cookies et CSRF fiables.
// En production, configurer Nginx pour servir dashboard et /api sous le même domaine.
const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, ''),
  withCredentials: true,
  withXSRFToken: true,
  xsrfCookieName: 'csrftoken',
  xsrfHeaderName: 'X-CSRFToken',
  timeout: 30000,
  headers: { Accept: 'application/json' },
});

// Aucun JWT en JS : Django gère sessionid (HttpOnly) et csrftoken.
// Pour chaque formulaire, les erreurs réelles sont affichées sans les avaler.
export function apiError(error) {
  if (!axios.isAxiosError(error)) return error?.message || 'Erreur inattendue.';
  const payload = error.response?.data;
  const fields = payload?.error?.fields || payload?.fields || payload;
  if (error.response?.status === 401) return 'Session expirée ou identifiants invalides.';
  if (error.response?.status === 403) return 'Accès refusé : droits insuffisants ou jeton CSRF incorrect.';
  if (error.response?.status === 409) return payload?.error?.message || 'Conflit de modification : rechargez les données.';
  const messages = fields && typeof fields === 'object'
    ? Object.entries(fields).filter(([k]) => !['error', 'detail', 'code', 'message'].includes(k))
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(', ') : String(value)}`)
    : [];
  return [payload?.error?.message || payload?.detail || error.message, ...messages].filter(Boolean).join(' · ');
}

// Lecture paginée (DRF PageNumberPagination). Les URL suivantes doivent rester
// dans le chemin /api/ : aucune URL externe n'est autorisée dans la pagination.
export async function allPages(path, params = {}) {
  let next = path;
  const results = [];
  let requestParams = { ...params };
  for (let page = 0; next && page < 100; page += 1) {
    const { data } = await api.get(next, { params: requestParams });
    if (Array.isArray(data)) return data;
    results.push(...(data.results || []));
    if (!data.next) break;
    const parsed = new URL(data.next, window.location.origin);
    if (!parsed.pathname.startsWith('/api/')) throw new Error('Pagination en dehors de /api refusée');
    // Django peut publier un lien absolu pointant vers son port interne ; on
    // n'utilise jamais cet hôte, uniquement son chemin API local.
    next = `${parsed.pathname.replace(/^\/api(?=\/)/, '')}${parsed.search}`;
    requestParams = {};
  }
  return results;
}

export default api;
