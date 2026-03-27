import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: 'login', loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) },
  { path: 'onboarding', canActivate: [authGuard], loadComponent: () => import('./features/onboarding/wizard/wizard.component').then(m => m.WizardComponent) },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell.component').then(m => m.ShellComponent),
    children: [
      { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
      { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent) },
      { path: 'ingestion', loadComponent: () => import('./features/ingestion/monitor/monitor.component').then(m => m.MonitorComponent) },
      { path: 'kg-explorer', loadComponent: () => import('./features/kg-explorer/explorer/explorer.component').then(m => m.ExplorerComponent) },
      { path: 'sdl-editor', loadComponent: () => import('./features/sdl-editor/editor.component').then(m => m.SdlEditorComponent) },
      { path: 'query-lab', loadComponent: () => import('./features/query-lab/lab/lab.component').then(m => m.QueryLabComponent) },
      { path: 'audit', loadComponent: () => import('./features/audit/log.component').then(m => m.AuditLogComponent) },
    ],
  },
  { path: '**', redirectTo: '/login' },
];
