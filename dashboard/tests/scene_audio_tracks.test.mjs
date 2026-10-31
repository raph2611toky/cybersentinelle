import assert from 'node:assert/strict';
import { draftSceneSources, publishedSceneSources, adminMediaUrl } from '../src/lib/sceneAudio.js';

globalThis.window = { location: { origin:'https://dashboard.safidiko.ik0m.tech' } };
const base = '/api/editor/studio/media/';
const languages = [{id:'lang-fr',code:'fr'}, {id:'lang-mg',code:'mg'}];
const fr = {
  id:'scene-fr',noeud:'start',langue:'lang-fr',statut:'READY',
  video:'video-fr',video_source_url:base+'original/file/',video_finale_url:base+'final/file/',
  audio_finale_url:base+'fr-track/file/',audio_embedded:true,
};
const mg = {id:'scene-mg',noeud:'start',langue:'lang-mg',statut:'READY',audio_finale_url:base+'mg-track/file/'};
const frOnly = draftSceneSources({scenes:[fr],languages,media:[],nodeId:'start',lang:'fr'});
assert.equal(frOnly.video,base+'original/file/');
assert.equal(frOnly.audio,base+'fr-track/file/');
assert.equal(frOnly.embeddedAudio,false);
assert.equal(frOnly.audioLanguage,'fr');
const mgFallback = draftSceneSources({scenes:[fr],languages,media:[],nodeId:'start',lang:'mg'});
assert.equal(mgFallback.audioLanguage,'fr');
assert.equal(mgFallback.audio,frOnly.audio);
const mgReady = draftSceneSources({scenes:[fr,mg],languages,media:[],nodeId:'start',lang:'mg'});
assert.equal(mgReady.video,frOnly.video);
assert.equal(mgReady.audio,base+'mg-track/file/');
assert.equal(mgReady.audioLanguage,'mg');
assert.equal(mgReady.embeddedAudio,false);
const published = publishedSceneSources({media:{fr:{video_url:'/api/v1/2026/media/fr.mp4',audio_url:'/api/v1/2026/media/fr.mp3'},mg:{video_url:'/api/v1/2026/media/mg.mp4',audio_url:'/api/v1/2026/media/mg.mp3'}},audio_tracks:{fr:{url:'/api/v1/2026/media/fr.mp3'},mg:{url:'/api/v1/2026/media/mg.mp3'}}},'mg');
assert.equal(published.video,'/api/v1/2026/media/fr.mp4');
assert.equal(published.audio,'/api/v1/2026/media/mg.mp3');
assert.equal(published.embeddedAudio,false);
assert.equal(adminMediaUrl('javascript:alert(1)'),'');
assert.equal(adminMediaUrl('https://malicious.example/invalid'),'');
assert.equal(adminMediaUrl('https://internal:8000/api/editor/studio/media/asset/file/'),base+'asset/file/');
const frWithVariants = {
  ...fr,
  audio_variants: [
    {id:'old',titre:'Ancienne narration',audio_url:base+'old/file/',audio:'old-file',selected:false},
    {id:'new',titre:'Nouvelle narration',audio_url:base+'new/file/',audio:'new-file',selected:true},
  ],
};
const alternative = draftSceneSources({scenes:[frWithVariants],languages,media:[],nodeId:'start',lang:'fr',variantId:'old'});
assert.equal(alternative.audio,base+'old/file/');
assert.equal(alternative.video,base+'original/file/');
assert.equal(alternative.embeddedAudio,false);
const noFrench = {...fr,statut:'DRAFT',audio:null,audio_finale_url:null,video_finale_url:null};
const emptyTrack=draftSceneSources({scenes:[noFrench],languages,media:[],nodeId:'start',lang:'fr'});
assert.equal(emptyTrack.audio,'');
assert.equal(emptyTrack.audioLanguage,null);
console.log('21 contrôles sources FR/MG, variantes et absence de piste réussis.');
