const localized = (fr, mg = '') => ({ fr, mg });

export function newGraph(title) {
  return {
    nodes: [
      { id: 'start', type: 'story', position: { x: 240, y: 20 }, data: { kind: 'scene', title: localized('Introduction : ' + title), text: localized('Une situation fictive commence.'), mediaId: '' } },
      { id: 'decision-1', type: 'story', position: { x: 240, y: 190 }, data: { kind: 'decision', title: localized('Que faire ?'), text: localized('Choisissez une réaction.'), options: [{ id: 'option-a', label: localized('Demander de l’aide') }, { id: 'option-b', label: localized('Ignorer la situation') }] } },
      { id: 'ending-1', type: 'story', position: { x: 45, y: 405 }, data: { kind: 'ending', title: localized('Une aide adaptée'), text: localized('Un adulte de confiance accompagne la personne.') } },
      { id: 'ending-2', type: 'story', position: { x: 460, y: 405 }, data: { kind: 'ending', title: localized('Une autre conséquence'), text: localized('Il est toujours possible de demander de l’aide.') } },
    ],
    edges: [
      { id: 'edge-1', source: 'start', target: 'decision-1', type: 'smoothstep' },
      { id: 'edge-2', source: 'decision-1', sourceHandle: 'option-a', target: 'ending-1', type: 'smoothstep', label: 'Aide' },
      { id: 'edge-3', source: 'decision-1', sourceHandle: 'option-b', target: 'ending-2', type: 'smoothstep', label: 'Autre choix' },
    ],
  };
}

export const initialStories = [
  { id: 'aza-zaraina', title: 'Aza zaraina', theme: 'Diffusion non consentie', status: 'published', language: 'FR / MG', updatedAt: '2026-10-29T12:00:00Z', graph: newGraph('Aza zaraina') },
  { id: 'tsy-irery', title: 'Tsy irery', theme: 'Isolement et soutien', status: 'published', language: 'FR / MG', updatedAt: '2026-10-29T09:00:00Z', graph: newGraph('Tsy irery') },
  { id: 'aza-manaiky', title: 'Aza manaiky', theme: 'Pressions et chantage', status: 'draft', language: 'FR / MG', updatedAt: '2026-10-30T08:00:00Z', graph: newGraph('Aza manaiky') },
];

export const initialResources = [
  { id: 'res-1', title: 'Reconnaître le chantage numérique', type: 'Conseil', status: 'draft', url: '' },
  { id: 'res-2', title: 'Que faire face à une menace ?', type: 'Guide', status: 'draft', url: '' },
  { id: 'res-3', title: 'Trouver une aide officielle', type: 'Lien externe', status: 'draft', url: '' },
];
