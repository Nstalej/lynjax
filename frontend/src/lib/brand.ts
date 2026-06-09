export const brandTokens = {
  colors: {
    deepNavy: '#083B5C',
    signalBlue: '#0E7490',
    traceTeal: '#2DD4BF',
    iceBackground: '#F2FAF8',
    slateText: '#0F172A',
    mutedLine: '#B7CDD1',
  },
  tagline: 'Lynjax - Intelligent Network Visibility',
};

export const assessmentSummary = {
  target: 'Segmento Lab /24',
  owner: 'Equipo de Visibilidad',
  updatedAt: new Date('2026-06-08T09:00:00-05:00'),
  checks: [
    { name: 'Descubrimiento Controlado', state: 'Completo', result: '23 activos detectados' },
    { name: 'Exposición de Servicios', state: 'En Curso', result: '7 servicios para validar' },
    { name: 'Evidencia Técnica', state: 'Listo', result: '12 artefactos vinculados' },
  ],
};

export const formatUpdatedAt = (date: Date) =>
  new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
