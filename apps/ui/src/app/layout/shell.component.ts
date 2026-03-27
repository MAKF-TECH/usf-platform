import { Component, ChangeDetectionStrategy, inject, signal } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService } from '../core/auth/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'usf-shell',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './shell.component.html',
  styleUrl: './shell.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ShellComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  user = this.auth.currentUser;
  sidebarCollapsed = signal(false);

  navItems = [
    { path: '/dashboard', icon: '⊞', label: 'Dashboard' },
    { path: '/ingestion', icon: '↓', label: 'Ingestion' },
    { path: '/kg-explorer', icon: '◉', label: 'KG Explorer' },
    { path: '/sdl-editor', icon: '✎', label: 'SDL Editor' },
    { path: '/query-lab', icon: '▶', label: 'Query Lab' },
    { path: '/audit', icon: '☰', label: 'Audit Log' },
  ];

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
