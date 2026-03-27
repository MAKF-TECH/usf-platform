import {
  Component, ChangeDetectionStrategy, inject, signal
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../../core/auth/auth.service';

@Component({
  selector: 'usf-login',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginComponent {
  private auth = inject(AuthService);
  private router = inject(Router);

  email = signal('');
  password = signal('');
  isLoading = signal(false);
  error = signal('');

  async submit(): Promise<void> {
    if (!this.email() || !this.password()) {
      this.error.set('Please enter your email and password.');
      return;
    }
    this.isLoading.set(true);
    this.error.set('');
    try {
      await this.auth.login(this.email(), this.password());
      this.router.navigate(['/dashboard']);
    } catch (e: any) {
      this.error.set(e?.message ?? 'Login failed. Please try again.');
    } finally {
      this.isLoading.set(false);
    }
  }
}
