import {
  Component, ChangeDetectionStrategy, inject, signal, computed
} from '@angular/core';
import { MockService } from '../../../core/api/mock.service';
import { IngestionJob, LayerTrace } from '../../../core/models';
import { LayerDebugPanelComponent } from '../../../shared/components/layer-debug-panel/layer-debug-panel.component';
import { RelativeTimePipe } from '../../../shared/pipes/relative-time.pipe';
import { NgxEchartsDirective } from 'ngx-echarts';
import type { EChartsOption } from 'echarts';
import { DecimalPipe, PercentPipe } from '@angular/common';

@Component({
  selector: 'usf-monitor',
  standalone: true,
  imports: [LayerDebugPanelComponent, RelativeTimePipe, NgxEchartsDirective, DecimalPipe, PercentPipe],
  templateUrl: './monitor.component.html',
  styleUrl: './monitor.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MonitorComponent {
  private mock = inject(MockService);

  jobs = signal(this.mock.ingestionJobs);
  selectedJob = signal<IngestionJob | null>(this.mock.ingestionJobs[0]);

  selectedTrace = computed<LayerTrace | null>(() => {
    const job = this.selectedJob();
    if (!job?.l1Trace) return null;
    return {
      layer1: job.l1Trace,
      layer2: { named_graph: `usf://tenant/acme-bank/source/${job.id}`, ontology_version: 'FIBO-v3.2.1', triples_in_scope: job.triplesAdded },
    };
  });

  confidenceHistogramOption = computed<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    grid: { top: 10, right: 10, bottom: 30, left: 40 },
    xAxis: {
      type: 'category',
      data: ['0.5', '0.6', '0.7', '0.8', '0.85', '0.9', '0.95', '0.98', '1.0'],
      axisLabel: { color: '#9299b8', fontSize: 10 },
      axisLine: { lineStyle: { color: '#333750' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#9299b8', fontSize: 10 },
      splitLine: { lineStyle: { color: '#333750', type: 'dashed' } },
    },
    series: [{
      type: 'bar',
      data: [4, 8, 22, 58, 142, 389, 1204, 892, 702],
      itemStyle: { color: '#3b5bdb', borderRadius: [3, 3, 0, 0] },
    }],
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#1a1d27',
      borderColor: '#333750',
      textStyle: { color: '#f1f3f9', fontSize: 12 },
    },
  }));

  statusBadgeClass(status: string): string {
    return { running: 'badge-info', completed: 'badge-success', failed: 'badge-error', pending: 'badge-neutral' }[status] ?? 'badge-neutral';
  }

  typeIcon(type: string): string {
    return { csv: '📊', pdf: '📄', api: '🔌', stream: '📡' }[type] ?? '📦';
  }
}
