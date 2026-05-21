import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';

/** React-обёртка Plotly поверх лёгкого дистрибутива plotly.js-dist-min. */
export const Plot = createPlotlyComponent(Plotly);
