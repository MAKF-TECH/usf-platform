import { Injectable, signal, computed } from '@angular/core';

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  tenantId: string;
  tenantName: string;
  role: 'admin' | 'analyst' | 'viewer';
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _token = signal<string | null>(null);
  private _user = signal<AuthUser | null>(null);

  readonly isAuthenticated = computed(() => !!this._token());
  readonly currentUser = computed(() => this._user());
  readonly token = computed(() => this._token());

  login(email: string, password: string): Promise<void> {
    // Mock login — in production, POST /api/auth/login
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (email && password.length >= 4) {
          const user: AuthUser = {
            id: 'user-001',
            email,
            name: email.split('@')[0],
            tenantId: 'tenant-acme-bank',
            tenantName: 'Acme Bank',
            role: 'admin',
          };
          this._user.set(user);
          this._token.set('mock-jwt-token-' + Date.now());
          resolve();
        } else {
          reject(new Error('Invalid credentials'));
        }
      }, 800);
    });
  }

  logout(): void {
    this._token.set(null);
    this._user.set(null);
  }

  getToken(): string | null {
    return this._token();
  }
}
