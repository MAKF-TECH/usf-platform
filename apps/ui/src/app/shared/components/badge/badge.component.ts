import { Component, ChangeDetectionStrategy, input } from '@angular/core';
import { NgClass } from '@angular/common';

export type BadgeVariant = 'success' | 'warning' | 'error' | 'info' | 'default';

@Component({
  selector: 'usf-badge',
  standalone: true,
  imports: [NgClass],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="badge"
      [ngClass]="{
        'badge-success': variant() === 'success',
        'badge-warning': variant() === 'warning',
        'badge-error': variant() === 'error',
        'badge-info': variant() === 'info',
        'badge-default': variant() === 'default'
      }"
    >{{ text() }}</span>
  `,
  styles: [`
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 0.125rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 600;
      line-height: 1.25rem;
    }
    .badge-success  { background: #d1fae5; color: #065f46; }
    .badge-warning  { background: #fef3c7; color: #92400e; }
    .badge-error    { background: #fee2e2; color: #991b1b; }
    .badge-info     { background: #dbeafe; color: #1e40af; }
    .badge-default  { background: #f3f4f6; color: #374151; }
  `],
})
export class BadgeComponent {
  variant = input<BadgeVariant>('default');
  text = input<string>('');
}
