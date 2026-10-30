/** Os endpoints de auditoria são declarados no arquivo único de configuração da plataforma. */
import { Injectable, inject } from '@angular/core';
import { ApiConfiguration as PlatformConfiguration } from '../../core/config';
@Injectable({providedIn: 'root'})
export class ApiConfiguration {
  private readonly platform = inject(PlatformConfiguration);
  get baseUrl(): string { return this.platform.auditBaseUrl; }
  get pollInterval(): number { return this.platform.pollInterval; }
}
