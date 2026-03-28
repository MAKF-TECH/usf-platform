import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) },
  { path: 'onboarding', loadComponent: () => import('./features/onboarding/wizard/wizard.component').then(m => m.WizardComponent) },
  { path: 'dashboard', loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent), canActivate: [authGuard] },
  { path: 'ingestion', loadComponent: () => import('./features/ingestion/monitor/monitor.component').then(m => m.MonitorComponent), canActivate: [authGuard] },
  { path: 'kg-explorer', loadComponent: () => import('./features/kg-explorer/explorer/explorer.component').then(m => m.ExplorerComponent), canActivate: [authGuard] },
  { path: 'sdl-editor', loadComponent: () => import('./features/sdl-editor/editor.component').then(m => m.SdlEditorComponent), canActivate: [authGuard] },
  { path: 'query-lab', loadComponent: () => import('./features/query-lab/lab/lab.component').then(m => m.QueryLabComponent), canActivate: [authGuard] },
  { path: 'audit', loadComponent: () => import('./features/audit/log.component').then(m => m.AuditLogComponent), canActivate: [authGuard] },
];
