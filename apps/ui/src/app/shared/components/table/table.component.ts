import {
  Component,
  ChangeDetectionStrategy,
  input,
  signal,
  computed,
} from '@angular/core';
import { NgClass } from '@angular/common';
import { TableColumn } from './table.types';

@Component({
  selector: 'usf-table',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="table-wrapper">
      <!-- Loading overlay -->
      @if (loading()) {
        <div class="table-loading" role="status" aria-label="Loading data">
          <span class="loading-spinner"></span>
        </div>
      }

      <!-- Table -->
      <table class="data-table" [class.is-loading]="loading()">
        <thead>
          <tr>
            @for (col of columns(); track col.key) {
              <th
                [style.width]="col.width ?? 'auto'"
                [class.sortable]="col.sortable"
                [ngClass]="'align-' + (col.align ?? 'left')"
                (click)="col.sortable ? toggleSort(col.key) : null"
                [attr.aria-sort]="col.sortable ? ariaSortFor(col.key) : null"
              >
                {{ col.label }}
                @if (col.sortable) {
                  <span class="sort-icon" aria-hidden="true">
                    @if (sortColumn() === col.key) {
                      {{ sortDirection() === 'asc' ? '↑' : '↓' }}
                    } @else {
                      ↕
                    }
                  </span>
                }
              </th>
            }
          </tr>
        </thead>
        <tbody>
          @for (row of pagedRows(); track $index) {
            <tr>
              @for (col of columns(); track col.key) {
                <td [ngClass]="'align-' + (col.align ?? 'left')">
                  {{ getCell(row, col.key) }}
                </td>
              }
            </tr>
          } @empty {
            <tr>
              <td [attr.colspan]="columns().length" class="empty-state">
                No data available.
              </td>
            </tr>
          }
        </tbody>
      </table>

      <!-- Pagination -->
      @if (totalPages() > 1) {
        <div class="pagination" role="navigation" aria-label="Pagination">
          <button
            class="page-btn"
            [disabled]="currentPage() === 1"
            (click)="goToPage(currentPage() - 1)"
            aria-label="Previous page"
          >←</button>
          <span class="page-info">
            Page {{ currentPage() }} of {{ totalPages() }}
            <span class="text-muted">({{ sortedData().length }} rows)</span>
          </span>
          <button
            class="page-btn"
            [disabled]="currentPage() === totalPages()"
            (click)="goToPage(currentPage() + 1)"
            aria-label="Next page"
          >→</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .table-wrapper { position: relative; width: 100%; }
    .table-loading {
      position: absolute; inset: 0; background: rgba(255,255,255,0.6);
      display: flex; align-items: center; justify-content: center; z-index: 10;
    }
    .loading-spinner {
      width: 24px; height: 24px; border: 3px solid #e5e7eb;
      border-top-color: #6366f1; border-radius: 50%;
      animation: spin 0.7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    .data-table.is-loading { opacity: 0.4; pointer-events: none; }
    th, td { padding: 0.5rem 0.75rem; border-bottom: 1px solid #e5e7eb; text-align: left; }
    th { background: #f9fafb; font-weight: 600; color: #374151; user-select: none; }
    th.sortable { cursor: pointer; }
    th.sortable:hover { background: #f3f4f6; }
    .sort-icon { margin-left: 0.25rem; color: #9ca3af; font-size: 0.75rem; }
    .align-center { text-align: center; }
    .align-right { text-align: right; }
    .empty-state { text-align: center; color: #9ca3af; padding: 2rem; }
    .pagination {
      display: flex; align-items: center; justify-content: flex-end;
      gap: 0.75rem; padding: 0.75rem 0; font-size: 0.875rem;
    }
    .page-btn {
      padding: 0.25rem 0.75rem; border: 1px solid #d1d5db; border-radius: 0.375rem;
      background: #fff; cursor: pointer;
    }
    .page-btn:disabled { opacity: 0.4; cursor: not-allowed; }
    .page-btn:not(:disabled):hover { background: #f9fafb; }
    .text-muted { color: #9ca3af; }
  `],
})
export class TableComponent<T extends Record<string, unknown>> {
  columns = input<TableColumn[]>([]);
  data = input<T[]>([]);
  loading = input(false);

  pageSize = signal(20);
  currentPage = signal(1);
  sortColumn = signal<string | null>(null);
  sortDirection = signal<'asc' | 'desc'>('asc');

  sortedData = computed<T[]>(() => {
    const col = this.sortColumn();
    const dir = this.sortDirection();
    const rows = [...this.data()];
    if (!col) return rows;
    return rows.sort((a, b) => {
      const av = (a[col] ?? '') as string | number;
      const bv = (b[col] ?? '') as string | number;
      if (av === bv) return 0;
      const gt = av > bv ? 1 : -1;
      return dir === 'asc' ? gt : -gt;
    });
  });

  totalPages = computed(() =>
    Math.max(1, Math.ceil(this.sortedData().length / this.pageSize()))
  );

  pagedRows = computed<T[]>(() => {
    const start = (this.currentPage() - 1) * this.pageSize();
    return this.sortedData().slice(start, start + this.pageSize());
  });

  toggleSort(key: string): void {
    if (this.sortColumn() === key) {
      this.sortDirection.update(d => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      this.sortColumn.set(key);
      this.sortDirection.set('asc');
    }
    this.currentPage.set(1);
  }

  goToPage(page: number): void {
    const clamped = Math.max(1, Math.min(page, this.totalPages()));
    this.currentPage.set(clamped);
  }

  getCell(row: T, key: string): unknown {
    return row[key] ?? '';
  }

  ariaSortFor(key: string): string {
    if (this.sortColumn() !== key) return 'none';
    return this.sortDirection() === 'asc' ? 'ascending' : 'descending';
  }
}
