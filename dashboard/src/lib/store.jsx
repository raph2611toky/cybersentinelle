import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { authApi, storyApi, resourceApi, studioApi, publicationApi, normalizeStory, normalizeResource } from '../services/editor';
import { apiError } from '../services/api';

const AdminContext = createContext(null);
const EMPTY = { stories:[], nodes:[], options:[], resources:[], sources:[], media:[], voices:[], scenes:[], jobs:[], releases:[], languages:[] };

export function AdminProvider({ children }) {
  const [auth, setAuth] = useState({ authed:false, loading:true, user:null });
  const [data, setData] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const epoch = useRef(0);

  const refresh = useCallback(async () => {
    const currentEpoch=epoch.current;
    const tasks = {
      stories:storyApi.list(), nodes:storyApi.nodes(), options:storyApi.options(), resources:resourceApi.list(), sources:resourceApi.sources(),
      media:studioApi.media(), voices:studioApi.voices(), scenes:studioApi.scenes(),
      jobs:studioApi.jobs(), releases:publicationApi.releases(), languages:studioApi.languages(),
    };
    const keys = Object.keys(tasks);
    const responses = await Promise.allSettled(Object.values(tasks));
    const failures = [];
    const received={};
    responses.forEach((result,i)=>{
      if(result.status==='fulfilled') received[keys[i]]=(result.value||[]).map(v=>keys[i]==='stories'?normalizeStory(v):keys[i]==='resources'?normalizeResource(v):v);
      else failures.push(`${keys[i]} : ${apiError(result.reason)}`);
    });
    if(epoch.current===currentEpoch) {
      setData(prev=>({...prev,...received}));
      setError(failures.join(' | '));
    }
    return failures;
  }, []);

  useEffect(() => {
    let alive=true;
    (async () => {
      try {
        await authApi.csrf();
        const { data:resp }=await authApi.me();
        if(alive) setAuth({authed:true,loading:false,user:resp.user});
        // Après authentification : aucune récupération de contenus avant autorisation.
        if(alive) await refresh();
      } catch {
        if(alive) setAuth({authed:false,loading:false,user:null});
      }
    })();
    return () => {alive=false};
  },[refresh]);

  // Refresh only editorial lists while Google translation workers are active.
  useEffect(()=>{
    if(!auth.authed)return;
    const pending=[...data.stories,...data.resources,...data.sources].some(
      item=>item.translation_state?.state==='PENDING'
    );
    if(!pending)return;
    let alive=true;
    const timer=setInterval(async()=>{
      try{
        const [stories,resources,sources]=await Promise.all([storyApi.list(),resourceApi.list(),resourceApi.sources()]);
        if(alive)setData(old=>({...old,
          stories:stories.map(normalizeStory),resources:resources.map(normalizeResource),sources}));
      }catch{ /* Keep the last consistent snapshot; user can retry refresh. */ }
    },8000);
    return ()=>{alive=false;clearInterval(timer)};
  },[auth.authed,data.stories,data.resources,data.sources]);

  const login = useCallback(async (username,password) => {
    setBusy(true);setError('');
    const currentEpoch=++epoch.current;
    try {
      await authApi.csrf();
      const {data:res}=await authApi.login(username,password);
      if(epoch.current!==currentEpoch) return;
      setAuth({authed:true,loading:false,user:res.user});
      await refresh();
      return res.user;
    } catch(e) {setError(apiError(e));throw e} finally {setBusy(false)}
  },[refresh]);

  const logout = useCallback(async () => {
    ++epoch.current;
    try { await authApi.logout(); } finally {
      setAuth({authed:false,loading:false,user:null});setData(EMPTY);setError('');
    }
  },[]);

  const perform = useCallback(async (call) => {
    setBusy(true);setError('');
    try { const result=await call(); await refresh(); return result?.data ?? result; }
    catch(e){ const message=apiError(e);setError(message); throw new Error(message); }
    finally{setBusy(false)}
  },[refresh]);

  const addStory = useCallback(payload=>perform(()=>storyApi.create(payload)),[perform]);
  const updateStory = useCallback((id,patch)=>perform(()=>storyApi.update(id,patch)),[perform]);
  const removeStory = useCallback(id=>perform(()=>storyApi.delete(id)),[perform]);
  const addResource = useCallback(payload=>perform(()=>resourceApi.create(payload)),[perform]);
  const updateResource = useCallback((id,patch)=>perform(()=>resourceApi.update(id,patch)),[perform]);
  const removeResource = useCallback(id=>perform(()=>resourceApi.delete(id)),[perform]);

  const value=useMemo(()=>({ ...data, auth, busy, error, setError, refresh, login, logout,
    perform, addStory, updateStory, removeStory, addResource, updateResource, removeResource,
  }),[data,auth,busy,error,refresh,login,logout,perform,addStory,updateStory,removeStory,addResource,updateResource,removeResource]);
  return <AdminContext.Provider value={value}>{children}</AdminContext.Provider>;
}
export function useAdmin(){const context=useContext(AdminContext);if(!context)throw new Error('AdminProvider requis');return context}
