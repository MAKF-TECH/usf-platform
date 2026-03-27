import {
  Component, ChangeDetectionStrategy, inject, signal
} from '@angular/core';
import { MockService } from '../../../core/api/mock.service';
import { KgNode } from '../../../core/models';
import { GraphViewerComponent } from '../../../shared/components/graph-viewer/graph-viewer.component';
import { ProvOPanelComponent } from '../../../shared/components/prov-o-panel/prov-o-panel.component';
import { RdfCuriePipe } from '../../../shared/pipes/rdf-curie.pipe';
import { DecimalPipe } from '@angular/common';

@Component({
  selector: 'usf-explorer',
  standalone: true,
  imports: [GraphViewerComponent, ProvOPanelComponent, RdfCuriePipe, DecimalPipe],
  templateUrl: './explorer.component.html',
  styleUrl: './explorer.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ExplorerComponent {
  private mock = inject(MockService);

  nodes = signal(this.mock.kgNodes);
  edges = signal(this.mock.kgEdges);
  selectedIri = signal<string | null>(null);

  namedGraphs = signal([
    { name: 'finance', triples: 48291, icon: '💰' },
    { name: 'risk', triples: 62140, icon: '⚠' },
    { name: 'ops', triples: 18042, icon: '⚙' },
  ]);

  selectedEntity = signal<KgNode | null>(null);

  onNodeSelected(iri: string): void {
    this.selectedIri.set(iri);
    const node = this.nodes().find(n => n.iri === iri) ?? null;
    this.selectedEntity.set(node);
  }

  objectEntries(obj: Record<string, string>): [string, string][] {
    return Object.entries(obj);
  }

  entityProvenance = signal({
    '@type': 'prov:Entity',
    'prov:wasGeneratedBy': 'activity:ingest-run-001',
    'prov:wasAttributedTo': 'agent:docling-v2.1',
    'prov:generatedAtTime': '2024-01-15T10:23:14Z',
  });
}
