/** Configuração lida antes de iniciar Angular, sem recompilar por ambiente. */
import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

interface RuntimeConfiguration {apiBaseUrl: string; auditApiBaseUrl: string; chatbotApiBaseUrl: string; pollIntervalMs: number;}

@Injectable({providedIn: 'root'})
export class ApiConfiguration {
  private readonly http = inject(HttpClient);
  private configuration: RuntimeConfiguration | null = null;

  /** Um erro impede inicialização com um endpoint presumido. */
  async load(): Promise<void> {
    const value = await firstValueFrom(this.http.get<RuntimeConfiguration>('app-config.json'));
    // Um endpoint por módulo evita misturar versões e estados independentes.
    const endpoints = [value.apiBaseUrl, value.auditApiBaseUrl, value.chatbotApiBaseUrl];
    if (!endpoints.every(endpoint => typeof endpoint === 'string' && endpoint.trim().length > 0)) {
      throw new Error('Os três endpoints precisam estar definidos em app-config.json.');
    }
    const urls = endpoints.map(endpoint => new URL(endpoint, window.location.origin));
    if (!urls.every(url => ['http:', 'https:'].includes(url.protocol)) || !Number.isInteger(value.pollIntervalMs) || value.pollIntervalMs < 500) {
      throw new Error('Configuração da aplicação inválida.');
    }
    this.configuration = {
      ...value,
      apiBaseUrl: value.apiBaseUrl.replace(/\/$/, ''),
      auditApiBaseUrl: value.auditApiBaseUrl.replace(/\/$/, ''),
      chatbotApiBaseUrl: value.chatbotApiBaseUrl.replace(/\/$/, ''),
    };
  }

  get baseUrl(): string { if (!this.configuration) throw new Error('Configuração indisponível.'); return this.configuration.apiBaseUrl; }
  get auditBaseUrl(): string { if (!this.configuration) throw new Error('Configuração da auditoria indisponível.'); return this.configuration.auditApiBaseUrl; }
  get chatbotBaseUrl(): string { if (!this.configuration) throw new Error('Configuração do chatbot indisponível.'); return this.configuration.chatbotApiBaseUrl; }
  get pollInterval(): number { return this.configuration?.pollIntervalMs ?? 1500; }
}

// URLs são validadas no bootstrap; nenhum módulo supõe uma porta diferente.
