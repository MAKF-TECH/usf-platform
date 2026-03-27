import { Component, ChangeDetectionStrategy, input, signal } from '@angular/core';
import { LayerTrace } from '../../../core/models';
import { DecimalPipe, UpperCasePipe } from '@angular/common';

@Component({
  selector: 'usf-layer-debug-panel',
  standalone: true,
  imports: [DecimalPipe, UpperCasePipe],
  templateUrl: './layer-debug-panel.component.html',
  styleUrl: './layer-debug-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LayerDebugPanelComponent {
  trace = input<LayerTrace | null>(null);
  expanded = signal(true);
  activeLayer = signal<1 | 2 | 3 | 4>(3);
  layers = [1, 2, 3, 4] as const;
  layerNames: Record<number, string> = { 1: 'L1 Ingestion', 2: 'L2 Knowledge Graph', 3: 'L3 Orchestration', 4: 'L4 Consumption' };

  pct(val: number): string { return (val * 100).toFixed(1) + '%'; }
  confColor(v: number): string { return v >= 0.95 ? 'var(--usf-success)' : v >= 0.8 ? 'var(--usf-warning)' : 'var(--usf-error)'; }
  prettyJson(obj: object | undefined): string { return obj ? JSON.stringify(obj, null, 2) : ''; }

  hasData(l: number): boolean {
    const t = this.trace();
    if (!t) return false;
    return !!(l === 1 ? t.layer1 : l === 2 ? t.layer2 : l === 3 ? t.layer3 : t.layer4);
  }
}
