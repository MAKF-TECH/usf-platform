import { Component, ChangeDetectionStrategy, input, output, signal, computed } from '@angular/core';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';
import { KgNode, KgEdge } from '../../../core/models';
import { TitleCasePipe } from '@angular/common';

@Component({
  selector: 'usf-graph-viewer',
  standalone: true,
  imports: [NgxEchartsDirective, TitleCasePipe],
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
  layouts: Array<'force' | 'circular' | 'none'> = ['force', 'circular', 'none'];

  filteredNodes = computed(() => {
    const q = this.searchQuery().toLowerCase();
    const all = this.nodes();
    if (!q) return all.slice(0, this.maxNodes());
    return all.filter(n => n.label.toLowerCase().includes(q) || n.iri.toLowerCase().includes(q)).slice(0, this.maxNodes());
  });

  chartOption = computed<EChartsOption>(() => {
    const iris = new Set(this.filteredNodes().map(n => n.iri));
    const edges = this.edges().filter(e => iris.has(e.subject) && iris.has(e.object));
    const colorMap: Record<string, string> = { Entity: '#3b5bdb', Metric: '#7c3aed', Event: '#0ea5e9', Document: '#f59e0b', Context: '#10b981', Provenance: '#6b7280' };
    return {
      backgroundColor: 'transparent',
      tooltip: { trigger: 'item', backgroundColor: '#1a1d27', borderColor: '#333750', textStyle: { color: '#f1f3f9', fontSize: 12 }, extraCssText: 'border-radius:8px;padding:10px' },
      legend: [{ data: Object.keys(colorMap), textStyle: { color: '#9299b8', fontSize: 11 }, bottom: 8, icon: 'circle', itemWidth: 10, itemHeight: 10 }],
      series: [{
        type: 'graph',
        layout: this.layout(),
        data: this.filteredNodes().map(n => ({
          id: n.iri, name: n.label, category: n.ontologyClass,
          symbolSize: Math.min(8 + (n.degree ?? 0) * 2.5, 40),
          itemStyle: { color: colorMap[n.ontologyClass] ?? '#6b7280' },
          label: { show: this.showLabels(), formatter: '{b}', fontSize: 11, color: '#f1f3f9' },
        })),
        links: edges.map(e => ({ source: e.subject, target: e.object, lineStyle: { color: '#333750', width: 1, curveness: 0.1 } })),
        categories: Object.keys(colorMap).map(name => ({ name, itemStyle: { color: colorMap[name] } })),
        roam: true, zoom: 0.8,
        force: { repulsion: 300, edgeLength: [50, 150], gravity: 0.1, layoutAnimation: true },
        emphasis: { focus: 'adjacency' as const, scale: true },
        selectedMode: 'single' as const,
      }],
    };
  });

  onChartClick(params: any): void {
    if (params.dataType === 'node') this.nodeSelected.emit(params.data.id);
  }
}
