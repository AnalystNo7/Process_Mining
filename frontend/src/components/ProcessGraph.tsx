import {
  CompressOutlined,
  DownloadOutlined,
  FullscreenExitOutlined,
  FullscreenOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
} from '@ant-design/icons';
import { Button, Space, Tooltip } from 'antd';
import cytoscape from 'cytoscape';
import dagre from 'cytoscape-dagre';
import { type CSSProperties, useEffect, useMemo, useRef, useState } from 'react';

import type { CytoscapeElement } from '@/api/analytics';

cytoscape.use(dagre);

// Ниже этого масштаба «вписать» не опускается — крупные графы остаются
// читаемыми (пользователь панорамирует/зумит), а не превращаются в точку.
const MIN_FIT_ZOOM = 0.55;

function smartFit(cy: cytoscape.Core): void {
  cy.fit(undefined, 30);
  // Если граф большой и вписался слишком мелко — поднимаем до читаемого
  // масштаба и центрируем (остальное пользователь панорамирует/зумит).
  if (cy.zoom() < MIN_FIT_ZOOM) {
    cy.zoom(MIN_FIT_ZOOM);
    cy.center();
  }
}

const BADGE_W = 40;
const BADGE_SVG_H = 48;
const TERMINAL_HEIGHT = 44;

export interface GraphHighlight {
  nodeIds: string[];
  edgeKeys: string[];
}

const TERMINAL_LABELS: Record<string, string> = {
  start: 'Начало процесса (Вход)',
  end: 'Конец процесса (Выход)',
};

/** Левый сегмент узла со счётчиком кейсов — отдельный SVG, чтобы счётчик
 * попадал в экспорт PNG (cytoscape рендерит background-image в png). */
function badgeImage(count: number, height: number): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${BADGE_W}" height="${height}">` +
    `<rect width="${BADGE_W}" height="${height}" fill="#f5f5f5"/>` +
    `<line x1="${BADGE_W - 0.5}" y1="0" x2="${BADGE_W - 0.5}" y2="${height}" ` +
    `stroke="#d9d9d9" stroke-width="1"/>` +
    `<text x="${BADGE_W / 2}" y="${height / 2}" ` +
    `font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif" ` +
    `font-size="13" font-weight="600" fill="#595959" ` +
    `text-anchor="middle" dominant-baseline="central">${count}</text>` +
    `</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

const GRAPH_STYLE = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'text-valign': 'center',
      'text-halign': 'center',
      'text-wrap': 'wrap',
      'text-max-width': 'data(tw)',
      'font-size': 13,
      width: 'data(w)',
      shape: 'round-rectangle',
    },
  },
  {
    selector: 'node[kind = "operation"]',
    style: {
      height: 'label',
      padding: '10px',
      'background-color': '#ffffff',
      'border-color': '#d9d9d9',
      'border-width': 1,
      color: '#262626',
      'text-margin-x': BADGE_W / 2,
      'background-image': 'data(badge)',
      'background-fit': 'none',
      'background-width': BADGE_W,
      'background-height': '100%',
      'background-position-x': '0%',
      'background-position-y': '50%',
      'background-clip': 'node',
    },
  },
  {
    selector: 'node[kind = "start"], node[kind = "end"]',
    style: {
      height: TERMINAL_HEIGHT,
      'background-color': '#1677ff',
      'border-width': 0,
      color: '#ffffff',
      'font-weight': 600,
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
      'font-size': 11,
      color: '#8c8c8c',
      'text-background-color': '#ffffff',
      'text-background-opacity': 1,
      'text-background-padding': '2px',
    },
  },
  { selector: '.dim', style: { opacity: 0.18 } },
  {
    selector: 'node.hl',
    style: { 'border-color': '#fa8c16', 'border-width': 3 },
  },
  {
    selector: 'edge.hl',
    style: {
      'line-color': '#fa8c16',
      'target-arrow-color': '#fa8c16',
      color: '#fa8c16',
      width: 3,
    },
  },
];

function applyHighlight(cy: cytoscape.Core, highlight?: GraphHighlight): void {
  cy.batch(() => {
    cy.elements().removeClass('hl dim');
    if (!highlight || (!highlight.nodeIds.length && !highlight.edgeKeys.length)) {
      return;
    }
    const nodeSet = new Set(highlight.nodeIds);
    const edgeSet = new Set(highlight.edgeKeys);
    cy.nodes().forEach((node) => {
      node.addClass(nodeSet.has(node.id()) ? 'hl' : 'dim');
    });
    cy.edges().forEach((edge) => {
      edge.addClass(edgeSet.has(edge.id()) ? 'hl' : 'dim');
    });
  });
}

export function ProcessGraph({
  nodes,
  edges,
  highlight,
  height = 560,
}: {
  nodes: CytoscapeElement[];
  edges: CytoscapeElement[];
  highlight?: GraphHighlight;
  height?: number | string;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const highlightRef = useRef(highlight);
  highlightRef.current = highlight;
  const [expanded, setExpanded] = useState(false);

  const elements = useMemo(() => {
    const nodeEls = nodes.map((node) => {
      const kind = (node.data.kind as string) ?? 'operation';
      const count = Number(node.data.count ?? 0);
      const rawLabel = String(node.data.label ?? node.data.id);
      const label = TERMINAL_LABELS[kind] ?? rawLabel;
      const w =
        kind === 'operation'
          ? Math.min(320, Math.max(170, label.length * 6 + 70))
          : 200;
      return {
        data: {
          id: String(node.data.id),
          kind,
          label,
          count,
          w,
          tw: kind === 'operation' ? w - 64 : w - 24,
          badge: kind === 'operation' ? badgeImage(count, BADGE_SVG_H) : '',
        },
      };
    });
    const edgeEls = edges.map((edge) => ({
      data: {
        id: String(edge.data.id),
        source: String(edge.data.source),
        target: String(edge.data.target),
        count: Number(edge.data.count ?? 0),
      },
    }));
    return [...nodeEls, ...edgeEls];
  }, [nodes, edges]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const cy = cytoscape({
      container,
      elements,
      style: GRAPH_STYLE,
      layout: { name: 'dagre', rankDir: 'TB', nodeSep: 35, rankSep: 55 },
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.2,
    } as unknown as cytoscape.CytoscapeOptions);
    cyRef.current = cy;
    cy.one('layoutstop', () => smartFit(cy));
    applyHighlight(cy, highlightRef.current);

    // Контейнер может менять размер (flex-заполнение, ресайз окна) — держим
    // граф вписанным. rAF дебаунсит залпы изменений.
    let raf = 0;
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        if (cyRef.current) {
          cyRef.current.resize();
          smartFit(cyRef.current);
        }
      });
    });
    ro.observe(container);

    return () => {
      ro.disconnect();
      cancelAnimationFrame(raf);
      cy.destroy();
      cyRef.current = null;
    };
  }, [elements]);

  // При разворачивании/сворачивании контейнер меняет размер — пересчитываем
  // размеры cytoscape и вписываем граф заново.
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const id = requestAnimationFrame(() => {
      cy.resize();
      smartFit(cy);
    });
    return () => cancelAnimationFrame(id);
  }, [expanded]);

  // Esc — выход из полноэкранного режима.
  useEffect(() => {
    if (!expanded) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [expanded]);

  useEffect(() => {
    if (cyRef.current) {
      applyHighlight(cyRef.current, highlight);
    }
  }, [highlight]);

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

  const zoomBy = (factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  };

  const toolbar = (
    <Space size="small" wrap>
      <Tooltip title="Приблизить">
        <Button size="small" icon={<ZoomInOutlined />} onClick={() => zoomBy(1.25)} />
      </Tooltip>
      <Tooltip title="Отдалить">
        <Button size="small" icon={<ZoomOutOutlined />} onClick={() => zoomBy(0.8)} />
      </Tooltip>
      <Tooltip title="Вписать">
        <Button
          size="small"
          icon={<CompressOutlined />}
          onClick={() => cyRef.current && smartFit(cyRef.current)}
        />
      </Tooltip>
      <Tooltip title={expanded ? 'Свернуть' : 'На весь экран'}>
        <Button
          size="small"
          icon={expanded ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
          onClick={() => setExpanded((v) => !v)}
        />
      </Tooltip>
      <Tooltip title="Скачать PNG">
        <Button size="small" icon={<DownloadOutlined />} onClick={exportPng} />
      </Tooltip>
    </Space>
  );

  // fill — компонент заполняет flex-родителя (height="100%"), а не задаёт
  // фиксированную высоту. Используется, чтобы граф был вровень с панелью путей.
  const fill = !expanded && height === '100%';
  const wrapperStyle: CSSProperties =
    expanded
      ? {
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          background: '#fff',
          padding: 12,
          display: 'flex',
          flexDirection: 'column',
        }
      : fill
        ? { height: '100%', display: 'flex', flexDirection: 'column', minHeight: 0 }
        : {};

  return (
    <div style={wrapperStyle}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'flex-end',
          marginBottom: 8,
        }}
      >
        {toolbar}
      </div>
      <div
        ref={containerRef}
        style={{
          height: expanded || fill ? '100%' : height,
          flex: expanded || fill ? 1 : undefined,
          minHeight: 0,
          border: '1px solid #f0f0f0',
          borderRadius: 8,
        }}
      />
    </div>
  );
}
