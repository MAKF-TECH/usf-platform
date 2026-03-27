import { Component, ChangeDetectionStrategy, input } from '@angular/core';

@Component({
  selector: 'usf-prov-o-panel',
  standalone: true,
  templateUrl: './prov-o-panel.component.html',
  styleUrl: './prov-o-panel.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProvOPanelComponent {
  provenance = input<object | null>(null);

  entries(): Array<{ key: string; value: string }> {
    const p = this.provenance();
    if (!p) return [];
    return Object.entries(p).map(([k, v]) => ({
      key: k,
      value: typeof v === 'object' ? JSON.stringify(v) : String(v),
    }));
  }

  prettyJson(): string {
    const p = this.provenance();
    return p ? JSON.stringify(p, null, 2) : '';
  }
}
