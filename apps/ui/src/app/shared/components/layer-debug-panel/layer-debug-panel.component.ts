import {
  Component, ChangeDetectionStrategy, input, signal
} from '@angular/core';
import { DecimalPipe, UpperCasePipe } from '@angular/common';
import { LayerTrace } from '../../../core/models';

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

  layerNames: Record<number, string> = {
    1: 'L1 Ingestion',
    2: 'L2 Knowledge Graph',
    3: 'L3 Orchestration',
    4: 'L4 Consumption',
  };

  confidenceColor(val: number): string {
    if (val >= 0.95) return 'var(--usf-success)';
    if (val >= 0.80) return 'var(--usf-warning)';
    return 'var(--usf-error)';
  }

  pct(val: number): string {
    return (val * 100).toFixed(1) + '%';
  }

  prettyJson(obj: object | undefined): string {
    return obj ? JSON.stringify(obj, null, 2) : '';
  }

  hasLayerData(layer: 1 | 2 | 3 | 4): boolean {
    const t = this.trace();
    if (!t) return false;
    if (layer === 1) return !!t.layer1;
    if (layer === 2) return !!t.layer2;
    if (layer === 3) return !!t.layer3;
    if (layer === 4) return !!t.layer4;
    return false;
  }
}
