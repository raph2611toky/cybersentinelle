import api, { allPages } from './api';
const editor = '/editor';
const studio = `${editor}/studio`;

export const authApi = {
  csrf: () => api.get(`${editor}/auth/csrf/`),
  login: (identity, password) => api.post(`${editor}/auth/login/`, { username: identity, password }),
  me: () => api.get(`${editor}/auth/me/`),
  logout: () => api.post(`${editor}/auth/logout/`, {}),
};

export const translationApi = {
  status:(target_type,target_id)=>api.get(`${editor}/translations/status/`,{params:{target_type,target_id}}),
  retry:(target_type,target_id)=>api.post(`${editor}/translations/retry/`,{target_type,target_id}),
};

export const storyApi = {
  list: () => allPages(`${editor}/stories/`),
  create: data => api.post(`${editor}/stories/create/`, storyFormData(data)),
  update: (id, data) => api.patch(`${editor}/stories/${id}/partial-update/`, storyFormData(data)),
  delete: id => api.delete(`${editor}/stories/${id}/delete/`),
  nodes: () => allPages(`${editor}/nodes/`),
  options: () => allPages(`${editor}/options/`),
  graph: id => api.get(`${editor}/stories/${id}/graph/`),
  saveGraph: (id, graph, revision) => api.put(`${editor}/stories/${id}/graph/save/`, { graph, revision }),
  applyGraph: id => api.post(`${editor}/stories/${id}/graph/apply/`, {}),
};

export const resourceApi = {
  list: () => allPages(`${editor}/resources/`),
  sources: () => allPages(`${editor}/sources/`),
  createSource: data => api.post(`${editor}/sources/create/`,data),
  updateSource: (id,data) => api.patch(`${editor}/sources/${id}/partial-update/`,data),
  deleteSource: id => api.delete(`${editor}/sources/${id}/delete/`),
  create: data => api.post(`${editor}/resources/create/`, data),
  update: (id, data) => api.patch(`${editor}/resources/${id}/partial-update/`, data),
  delete: id => api.delete(`${editor}/resources/${id}/delete/`),
};

export const studioApi = {
  confirmRights: (id,licence) => api.post(`${studio}/media/${id}/rights-confirm/`, {licence}),
  prepareAudio: id => api.post(`${studio}/stories/${id}/prepare-audio/`, {}),
  media: () => allPages(`${studio}/media/`),
  upload: form => api.post(`${studio}/media/upload/`, form, { timeout: 120000 }),
  deleteMedia: id => api.delete(`${studio}/media/${id}/delete/`),
  updateMedia: (id, data) => api.patch(`${studio}/media/${id}/update/`, data),
  file: id => api.get(`${studio}/media/${id}/file/`, { responseType: 'blob', timeout: 120000 }),
  voices: () => allPages(`${studio}/voices/`),
  voiceCatalog: (provider, language) => api.get(`${studio}/voices/catalog/`, {params:{provider, language}, timeout:30000}),
  createVoice: data => api.post(`${studio}/voices/create/`, data),
  scenes: () => allPages(`${studio}/scenes/`),
  createScene: data => api.post(`${studio}/scenes/create/`, data),
  updateScene: (id, data) => api.patch(`${studio}/scenes/${id}/update/`, data),
  render: id => api.post(`${studio}/scenes/${id}/render/`, {}),
  variants: id => api.get(`${studio}/scenes/${id}/tracks/`),
  selectVariant: (sceneId, variantId) => api.post(`${studio}/scenes/${sceneId}/tracks/${variantId}/select/`, {}),
  clearVariant: sceneId => api.post(`${studio}/scenes/${sceneId}/tracks/clear/`, {}),
  tts: data => api.post(`${studio}/voices/generate/`, data),
  jobs: () => allPages(`${studio}/jobs/`),
  languages: () => allPages(`${editor}/languages/`),
};

export const publicationApi = {
  releases: () => allPages(`${editor}/releases/`),
  validate: () => api.get(`${editor}/releases/validate/`),
  publish: data => api.post(`${editor}/releases/publish/`, data),
  rollback: id => api.post(`${editor}/releases/${id}/rollback/`, {}),
};

export function normalizeStory(s) {
  return { ...s, title:s.titre_fr, titleMg:s.titre_mg, theme:s.theme_fr,
    themeMg:s.theme_mg, updatedAt:s.updated_at, language:'FR / MG',
    coverUrl: (()=>{ const url=s.image_cover_url; if(!url) return null; try {const parsed=new URL(url,window.location.origin);return parsed.pathname.startsWith('/media/') ? parsed.pathname+parsed.search : url;}catch{return url;} })(),
    status:({BROUILLON:'draft',A_CORRIGER:'draft',EN_RELECTURE:'review',APPROUVE:'ready',PUBLIE:'published',ARCHIVE:'draft'})[s.statut_editorial] || 'draft' };
}
export function normalizeResource(r) {
  return { ...r, title:r.titre_fr, titleMg:r.titre_mg,
    type:({INTERNAL:'Conseil',EXTERNAL:'Lien externe',CALL:'Téléphone'})[r.kind]||r.kind,
    url:r.href, status:r.statut_service==='ACTIVE'?'ready':'draft' };
}

/** Multipart for Tantara: Axios/browser choose the boundary automatically. */
export function storyFormData(values) {
  const form = new FormData();
  for (const [key, value] of Object.entries(values)) {
    if (value === null || value === undefined || value === '' || key === 'image_cover_url') continue;
    if (key === 'image_cover') {
      if (value instanceof File) form.append(key, value);
      continue;
    }
    if (Array.isArray(value)) value.forEach(item => form.append(key, String(item)));
    else form.append(key, String(value));
  }
  return form;
}
