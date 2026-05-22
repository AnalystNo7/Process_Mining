import { DownloadOutlined } from '@ant-design/icons';
import { Button } from 'antd';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { useEffect, useRef } from 'react';

import type { CytoscapeElement } from '@/api/analytics';

cytoscape.use(dagre);

const GRAPH_STYLE = [
  {
    selector: 'node',
    style: {
      'background-color': '#1677ff',
      label: 'data(label)',
      color: '#ffffff',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': 11,
      width: 'label',
      height: 34,
      padding: '10px',
      shape: 'round-rectangle',
      'text-wrap': 'wrap',
      'text-max-width': '150px',
    },
  },
  {
    selector: 'edge',
    style: {
      width: 2,
      'line-color': '#bfbfbf',
      'target-arrow-color': '#bfbfbf',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
      label: 'data(count)',
      'font-size': 10,
      color: '#8c8c8c',
      'text-background-color': '#ffffff',
      'text-background-opacity': 1,
      'text-background-padding': '2px',
    },
  },
];

export function ProcessGraph({
  nodes,
  edges,
  height = 520,
}: {
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
  height?: number;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const options = {
      container,
      elements: [...nodes, ...edges],
      style: GRAPH_STYLE,
      layout: { name: 'dagre', rankDir: 'LR', nodeSep: 28, rankSep: 70 },
      minZoom: 0.2,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
    };
    const cy = cytoscape(options as unknown as cytoscape.CytoscapeOptions);
    cyRef.current = cy;
    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges]);

  const exportPng = () => {
    const cy = cyRef.current;
    if (!cy) {
      return;
    }
    const blob = cy.png({ output: 'blob', bg: '#ffffff', full: true, scale: 2 }) as Blob;
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'process-graph.png';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      <div style={{ textAlign: 'right', marginBottom: 8 }}>
        <Button size="small" icon={<DownloadOutlined />} onClick={exportPng}>
          Скачать PNG
        </Button>
      </div>
      <div
        ref={containerRef}
        style={{ height, border: '1px solid #f0f0f0', borderRadius: 8 }}
      />
    </div>
  );
}
