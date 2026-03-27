import {
  Component, ChangeDetectionStrategy, inject, signal
} from '@angular/core';
import { MockService } from '../../../core/api/mock.service';
import { QueryResult } from '../../../core/models';
import { LayerDebugPanelComponent } from '../../../shared/components/layer-debug-panel/layer-debug-panel.component';
import { DecimalPipe, UpperCasePipe } from '@angular/common';

@Component({
  selector: 'usf-query-lab',
  standalone: true,
  imports: [LayerDebugPanelComponent, DecimalPipe, UpperCasePipe],
  templateUrl: './lab.component.html',
  styleUrl: './lab.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class QueryLabComponent {
  private mock = inject(MockService);

  activeTab = signal<'sql' | 'sparql' | 'nl' | 'mcp'>('sql');
  tabs: Array<'sql' | 'sparql' | 'nl' | 'mcp'> = ['sql', 'sparql', 'nl', 'mcp'];
  isLoading = signal(false);
  result = signal<QueryResult | null>(null);

  queries: Record<string, string> = {
    sql: `SELECT counterparty_name, SUM(exposure_amount) AS total_exposure\nFROM exposures\nWHERE sector = 'EU_FINANCIAL'\nGROUP BY counterparty_name\nORDER BY total_exposure DESC`,
    sparql: `PREFIX fibo: <https://spec.edmcouncil.org/fibo/ontology/>\nSELECT ?entity ?exposure WHERE {\n  ?entity a fibo:CreditExposure ;\n    fibo:hasCounterparty ?cp ;\n    fibo:exposureAmount ?exposure .\n  ?cp fibo:sector "EU_FINANCIAL" .\n} ORDER BY DESC(?exposure)`,
    nl: `What is the total exposure by counterparty in the EU financial sector?`,
    mcp: `await usf.query_metric({\n  metric: "total_exposure_by_counterparty",\n  dimensions: ["counterparty_name", "sector"],\n  filters: { sector: "EU_FINANCIAL" },\n  time_range: { start: "2024-01-01", end: "2024-03-31" },\n  context: "risk"\n})`,
  };

  queryInput = signal(this.queries['sql']);

  switchTab(tab: 'sql' | 'sparql' | 'nl' | 'mcp'): void {
    this.activeTab.set(tab);
    this.queryInput.set(this.queries[tab]);
  }

  isNumber(val: unknown): boolean {
    return typeof val === 'number';
  }

  execute(): void {
    this.isLoading.set(true);
    this.result.set(null);
    setTimeout(() => {
      this.result.set(this.mock.getMockQueryResult(this.queryInput(), this.activeTab()));
      this.isLoading.set(false);
    }, 800);
  }
}
