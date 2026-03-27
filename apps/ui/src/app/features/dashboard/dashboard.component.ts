import {
  Component, ChangeDetectionStrategy, inject, signal
} from '@angular/core';
import { MockService } from '../../core/api/mock.service';
import { GraphViewerComponent } from '../../shared/components/graph-viewer/graph-viewer.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';

@Component({
  selector: 'usf-dashboard',
  standalone: true,
  imports: [GraphViewerComponent, RelativeTimePipe, NgxEchartsDirective],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DashboardComponent {
  private mock = inject(MockService);

  nodes = signal(this.mock.kgNodes);
  edges = signal(this.mock.kgEdges);
  metrics = signal(this.mock.tenantMetrics);
  selectedNodeIri = signal<string | null>(null);

  activityFeed = signal([
    { icon: '✓', text: 'Ingestion completed: 3,421 triples added', time: new Date(Date.now() - 2 * 60000), color: 'var(--usf-success)' },
    { icon: '⚠', text: 'SHACL violation: 14 triples quarantined', time: new Date(Date.now() - 18 * 60000), color: 'var(--usf-warning)' },
    { icon: '▶', text: 'Query: finance/monthly_revenue via MCP (Claude)', time: new Date(Date.now() - 34 * 60000), color: 'var(--usf-info)' },
    { icon: '↓', text: 'New data source: Postgres DWH connected', time: new Date(Date.now() - 2 * 3600000), color: 'var(--usf-primary-500)' },
    { icon: '◉', text: '12,847 triples added from AML dataset', time: new Date(Date.now() - 5 * 3600000), color: 'var(--usf-success)' },
  ]);

  queryTrendOption: EChartsOption = {
    backgroundColor: 'transparent',
    grid: { top: 10, right: 10, bottom: 20, left: 40 },
    xAxis: {
      type: 'category',
      data: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      axisLine: { lineStyle: { color: '#333750' } },
      axisLabel: { color: '#9299b8', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#333750' } },
      splitLine: { lineStyle: { color: '#333750', type: 'dashed' } },
      axisLabel: { color: '#9299b8', fontSize: 11 },
    },
    series: [{
      type: 'line',
      data: [42, 87, 156, 234, 189, 67, 247],
      smooth: true,
      itemStyle: { color: '#3b5bdb' },
      areaStyle: { color: 'rgba(59,91,219,0.1)' },
      lineStyle: { width: 2 },
      symbol: 'none',
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1d27',
      borderColor: '#333750',
      textStyle: { color: '#f1f3f9', fontSize: 12 },
    },
  };

  contextDonutOption: EChartsOption = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      backgroundColor: '#1a1d27',
      borderColor: '#333750',
      textStyle: { color: '#f1f3f9', fontSize: 12 },
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: [
        { value: 48, name: 'Finance', itemStyle: { color: '#3b5bdb' } },
        { value: 35, name: 'Risk', itemStyle: { color: '#7c3aed' } },
        { value: 17, name: 'Ops', itemStyle: { color: '#10b981' } },
      ],
      label: { color: '#9299b8', fontSize: 11 },
    }],
  };

  statCards = [
    { label: 'Total Triples', value: '128,473', icon: '◉', color: 'var(--usf-primary-500)', trend: '+3,421 today' },
    { label: 'Active Contexts', value: '3', icon: '📐', color: 'var(--usf-node-context)', trend: 'finance · risk · ops' },
    { label: 'Data Sources', value: '4', icon: '🗄', color: 'var(--usf-node-event)', trend: '1 syncing' },
    { label: 'Queries Today', value: '247', icon: '▶', color: 'var(--usf-node-metric)', trend: '+12% vs yesterday' },
  ];
}
