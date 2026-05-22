/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_APP_NAME?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

// Дистрибутив Plotly без собственных типов — используется через react-plotly.js/factory.
declare module 'plotly.js-dist-min';

// Расширение раскладки графа без собственных типов.
declare module 'cytoscape-dagre';
