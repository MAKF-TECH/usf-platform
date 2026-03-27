import {
  Component, ChangeDetectionStrategy, inject, signal, computed
} from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TitleCasePipe } from '@angular/common';

const STEPS = [
  { id: 1, title: 'Tenant Setup', icon: '🏢' },
  { id: 2, title: 'Data Source', icon: '🗄' },
  { id: 3, title: 'Ontology', icon: '🧬' },
  { id: 4, title: 'Define Context', icon: '📐' },
  { id: 5, title: 'First Query', icon: '▶' },
];

@Component({
  selector: 'usf-wizard',
  standalone: true,
  imports: [FormsModule, TitleCasePipe],
  templateUrl: './wizard.component.html',
  styleUrl: './wizard.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WizardComponent {
  private router = inject(Router);

  steps = STEPS;
  currentStep = signal(1);
  isLoading = signal(false);

  // Step 1
  tenantName = signal('Acme Bank');
  industry = signal('Banking');
  industries = ['Banking', 'Healthcare', 'Energy', 'Retail', 'Insurance', 'Telecom'];

  // Step 2
  sourceType = signal<'warehouse' | 'files' | 'api' | 'stream'>('warehouse');
  connectionString = signal('postgresql://acme-dw.neon.tech/prod');
  connectionTested = signal(false);

  // Step 3
  ontologyLoaded = signal(false);
  mappingSuggestions = signal([
    { column: 'legal_entity_name', ontologyClass: 'fibo:LegalEntity', confidence: 0.97 },
    { column: 'account_id', ontologyClass: 'fibo:BankAccount', confidence: 0.91 },
    { column: 'transaction_amount', ontologyClass: 'fibo:MonetaryAmount', confidence: 0.88 },
    { column: 'counterparty_id', ontologyClass: 'fibo:Counterparty', confidence: 0.85 },
  ]);

  // Step 4
  contextName = signal('Risk Team');
  revenueDefinition = signal('net_interest_income');

  // Step 5
  queryResult = signal<string | null>(null);

  progress = computed(() => ((this.currentStep() - 1) / (STEPS.length - 1)) * 100);

  canProceed = computed(() => {
    switch (this.currentStep()) {
      case 1: return !!this.tenantName() && !!this.industry();
      case 2: return this.connectionTested();
      default: return true;
    }
  });

  next(): void {
    if (this.currentStep() < STEPS.length) this.currentStep.set(this.currentStep() + 1);
  }

  back(): void {
    if (this.currentStep() > 1) this.currentStep.set(this.currentStep() - 1);
  }

  testConnection(): void {
    this.isLoading.set(true);
    setTimeout(() => {
      this.isLoading.set(false);
      this.connectionTested.set(true);
    }, 1200);
  }

  loadOntology(): void {
    this.isLoading.set(true);
    setTimeout(() => {
      this.isLoading.set(false);
      this.ontologyLoaded.set(true);
    }, 1500);
  }

  runFirstQuery(): void {
    this.isLoading.set(true);
    this.queryResult.set(null);
    setTimeout(() => {
      this.isLoading.set(false);
      this.queryResult.set('✓ 12,847 triples · 3 contexts · FIBO-aligned. Your KG is ready!');
    }, 2500);
  }

  finish(): void {
    this.router.navigate(['/dashboard']);
  }
}
