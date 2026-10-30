/** Acesso HTTP único às funcionalidades documentais e ao chat do AI Ready. */
import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { ApiConfiguration } from '../../core/config';
import { AiReadyConfiguration, ChatResponse, Health, ProcessWorkspaceResponse, DocketSearchResponse, DocketAnswer } from './contracts';

@Injectable({providedIn: 'root'})
export class AiReadyApiService {
  private readonly http = inject(HttpClient);
  private readonly config = inject(ApiConfiguration);

  health() {
    return this.http.get<Health>(`${this.config.chatbotBaseUrl}/saude`);
  }

  configuration() {
    return this.http.get<AiReadyConfiguration>(`${this.config.chatbotBaseUrl}/ai-ready/configuracao`);
  }

  analyze(files: File[], tipoProcesso: 'civel' | 'trabalhista' = 'civel') {
    const data = new FormData();
    files.forEach(file => data.append('files', file, file.name));
    data.append('tipo_processo', tipoProcesso);
    return this.http.post<ProcessWorkspaceResponse>(`${this.config.chatbotBaseUrl}/ai-ready/analisar`, data);
  }

  chat(pergunta: string) {
    return this.http.post<ChatResponse>(`${this.config.chatbotBaseUrl}/ai-ready/chat`, {pergunta});
  }

  search(workspaceId: string, question: string) {
    return this.http.get<DocketSearchResponse>(
      `${this.config.chatbotBaseUrl}/ai-ready/${encodeURIComponent(workspaceId)}/buscar`,
      {params: {q: question}},
    );
  }

  askDocuments(workspaceId: string, question: string) {
    return this.http.post<DocketAnswer>(`${this.config.chatbotBaseUrl}/ai-ready/perguntar-autos`,
      {workspace_id: workspaceId, pergunta: question});
  }

  discard(workspaceId: string) {
    return this.http.delete<void>(`${this.config.chatbotBaseUrl}/ai-ready/${encodeURIComponent(workspaceId)}`);
  }
}
