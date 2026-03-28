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

  exploreNeighbors(): void {
    const iri = this.selectedIri();
    if (!iri) return;
    const neighborIris = new Set<string>();
    neighborIris.add(iri);
    for (const e of this.mock.kgEdges) {
      if (e.subject === iri) neighborIris.add(e.object);
      if (e.object === iri) neighborIris.add(e.subject);
    }
    this.nodes.set(this.mock.kgNodes.filter(n => neighborIris.has(n.iri)));
    this.edges.set(this.mock.kgEdges.filter(e => neighborIris.has(e.subject) && neighborIris.has(e.object)));
  }

  resetGraph(): void {
    this.nodes.set(this.mock.kgNodes);
    this.edges.set(this.mock.kgEdges);
  }
}
