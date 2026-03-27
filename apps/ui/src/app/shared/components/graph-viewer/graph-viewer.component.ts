import {
  Component, ChangeDetectionStrategy, input, output,
  signal, computed, effect, ViewChild, ElementRef
} from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';
import { KgNode, KgEdge } from '../../../core/models';

@Component({
  selector: 'usf-graph-viewer',
  standalone: true,
  imports: [NgxEchartsDirective],
  templateUrl: './graph-viewer.component.html',
  styleUrl: './graph-viewer.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class GraphViewerComponent {
  nodes = input<KgNode[]>([]);
  edges = input<KgEdge[]>([]);
  isLoading = input(false);

  nodeSelected = output<string>();

  searchQuery = signal('');
  layout = signal<'force' | 'circular' | 'none'>('force');
  showLabels = signal(true);
  maxNodes = signal(200);

  filteredNodes = computed(() => {
    const q = this.searchQuery().toLowerCase();
    const all = this.nodes();
    if (!q) return all.slice(0, this.maxNodes());
    return all.filter(n =>
      n.label.toLowerCase().includes(q) || n.iri.toLowerCase().includes(q)
    ).slice(0, this.maxNodes());
  });

  chartOption = computed<EChartsOption>(() => {
    const filteredIris = new Set(this.filteredNodes().map(n => n.iri));
    const visibleEdges = this.edges().filter(
      e => filteredIris.has(e.subject) && filteredIris.has(e.object)
    );

    return {
      backgroundColor: 'transparent',
      tooltip: {
        formatter: (params: any) => {
          if (params.dataType === 'node') {
            const props = params.data.properties as Record<string, string> | undefined;
            const propsHtml = props
              ? Object.entries(props).map(([k, v]) => `<div><span style="color:#5c6485">${k}:</span> ${v}</div>`).join('')
              : '';
            return `<div style="font-family:monospace;font-size:12px;max-width:280px">
              <div style="color:#9299b8;font-size:11px">${params.data.category}</div>
              <div style="font-weight:600;color:#f1f3f9;margin:2px 0">${params.data.name}</div>
              <div style="color:#5c6485;font-size:11px;margin-bottom:4px">${params.data.iri}</div>
              ${propsHtml}
            </div>`;
          }
          return `<span style="font-size:12px">${params.data.label || ''}</span>`;
        },
        backgroundColor: '#1a1d27',
        borderColor: '#333750',
        textStyle: { color: '#f1f3f9' },
        extraCssText: 'border-radius:8px;padding:10px',
      },
      toolbox: {
        feature: { restore: { title: 'Reset' }, saveAsImage: { title: 'Export PNG' } },
        right: 16,
        top: 16,
        iconStyle: { borderColor: '#9299b8' },
      },
      legend: [{
        data: ['Entity', 'Metric', 'Event', 'Document', 'Context', 'Provenance'],
        textStyle: { color: '#9299b8', fontSize: 12 },
        bottom: 8,
        icon: 'circle',
        itemWidth: 10,
        itemHeight: 10,
      }],
      series: [{
        type: 'graph',
        layout: this.layout(),
        data: this.filteredNodes().map(n => ({
          id: n.iri,
          name: n.label,
          iri: n.iri,
          category: n.ontologyClass,
          properties: n.properties,
          symbolSize: Math.min(8 + (n.degree ?? 0) * 2.5, 40),
          itemStyle: { color: this.nodeColor(n.ontologyClass) },
          label: {
            show: this.showLabels(),
            formatter: '{b}',
            fontSize: 11,
            color: '#f1f3f9',
            distance: 4,
          },
        })),
        links: visibleEdges.map(e => ({
          source: e.subject,
          target: e.object,
          label: { show: false, formatter: e.predicateLabel },
          lineStyle: { color: '#333750', width: 1, curveness: 0.1 },
        })),
        categories: [
          { name: 'Entity', itemStyle: { color: '#3b5bdb' } },
          { name: 'Metric', itemStyle: { color: '#7c3aed' } },
          { name: 'Event', itemStyle: { color: '#0ea5e9' } },
          { name: 'Document', itemStyle: { color: '#f59e0b' } },
          { name: 'Context', itemStyle: { color: '#10b981' } },
          { name: 'Provenance', itemStyle: { color: '#6b7280' } },
        ],
        roam: true,
        zoom: 0.8,
        force: {
          repulsion: 300,
          edgeLength: [50, 150],
          gravity: 0.1,
          layoutAnimation: true,
        },
        emphasis: {
          focus: 'adjacency',
          scale: true,
          label: { show: true },
        },
        selectedMode: 'single',
        lineStyle: { color: 'source', curveness: 0.1 },
      }],
    };
  });

  private nodeColor(cls: string): string {
    const map: Record<string, string> = {
      Entity: '#3b5bdb',
      Metric: '#7c3aed',
      Event: '#0ea5e9',
      Document: '#f59e0b',
      Context: '#10b981',
      Provenance: '#6b7280',
    };
    return map[cls] ?? '#6b7280';
  }

  onChartClick(params: any): void {
    if (params.dataType === 'node') {
      this.nodeSelected.emit(params.data.iri);
    }
  }

  layouts: Array<'force' | 'circular' | 'none'> = ['force', 'circular', 'none'];
}
