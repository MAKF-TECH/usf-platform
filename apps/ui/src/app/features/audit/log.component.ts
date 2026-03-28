import {
  Component, ChangeDetectionStrategy, inject, signal
} from '@angular/core';
import { MockService } from '../../core/api/mock.service';
import { AuditEntry } from '../../core/models';
import { UpperCasePipe } from '@angular/common';
import { ProvOPanelComponent } from '../../shared/components/prov-o-panel/prov-o-panel.component';
import { RelativeTimePipe } from '../../shared/pipes/relative-time.pipe';

@Component({
  selector: 'usf-audit-log',
  standalone: true,
  imports: [ProvOPanelComponent, RelativeTimePipe, UpperCasePipe],
  templateUrl: './log.component.html',
  styleUrl: './log.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuditLogComponent {
  private mock = inject(MockService);

  entries = signal(this.mock.auditEntries);
  expandedId = signal<string | null>(null);

  toggleExpand(id: string): void {
    this.expandedId.set(this.expandedId() === id ? null : id);
  }

  decisionClass(decision: string): string {
    return decision === 'allow' ? 'badge-success' : 'badge-error';
  }

  exportRdf(): void {
    const jsonLd = this.entries().map(e => ({
      '@context': 'https://www.w3.org/ns/prov',
      '@type': 'prov:Activity',
      'prov:startedAtTime': e.timestamp.toISOString(),
      'prov:wasAssociatedWith': `user:${e.user}`,
      'prov:used': `resource:${e.resource}`,
      'usf:action': e.action,
      'usf:context': e.context,
      'usf:decision': e.decision,
      ...((e.provenance as object) ?? {}),
    }));
    const blob = new Blob([JSON.stringify(jsonLd, null, 2)], { type: 'application/ld+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'usf-audit-export.jsonld';
    a.click();
    URL.revokeObjectURL(url);
  }
}
