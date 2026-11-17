/** Workspace do AI Ready para leitura, síntese e consulta de processos cíveis. */
import { CommonModule } from '@angular/common';
import { Component, ElementRef, OnDestroy, ViewChild, computed, inject, signal } from '@angular/core';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AiReadyApiService } from './core/ai-ready-api.service';
import { AiReadyConfiguration, ChatMessage, ProcessWorkspaceResponse, TimelineEvent, DocketSearchHit, DocketAnswer } from './core/contracts';
import { Notifications } from '../core/notifications';
import { CHAT_REFERENCE_OPTIONS, MAX_CHAT_REFERENCE_LENGTH, ChatReferenceType, buildContextualChatPrompt } from './core/chat-context';

type LocalDocument = {
  file: File;
  url: string;
};

type UiChatMessage = ChatMessage & {referenceLabel?: string};
type HubTab = 'panorama' | 'cronologia' | 'agenda' | 'provas' | 'documentos' | 'perguntas';
type PreflightItem = {id: string; title: string; help: string};
type HubShortcut = {tab: HubTab; number: string; title: string; description: string; outcome: string};

@Component({
  selector: 'app-chatbot-page',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <main class="ai-ready-page">
      <header class="ai-ready-heading">
        <div>
          <span class="eyebrow">AI READY / INTELIGÊNCIA JURÍDICA</span>
          <h1>Hub de inteligência processual</h1>
          <p>Da leitura dos autos à preparação da revisão jurídica: fatos, fontes, provas, datas mencionadas e perguntas contextualizadas.</p>
        </div>
        <div class="connection-pill" [attr.data-status]="connectionState()">
          <span class="connection-dot" aria-hidden="true"></span>
          <div>
            <strong>{{ connectionLabel() }}</strong>
            <small>{{ connectionDetail() }}</small>
          </div>
        </div>
      </header>

      <section class="ai-ready-layout">
        <aside class="document-rail surface">
          <div class="section-heading compact-heading">
            <div>
              <span class="eyebrow">Autos</span>
              <h2>Documentos do processo</h2>
            </div>
            @if (selectedFiles().length) {
              <span class="counter-badge">{{ selectedFiles().length }}</span>
            }
          </div>

          <div class="hub-area-select" role="group" aria-label="Tipo de processo">
            <label for="process-area-type">Área jurídica dos documentos</label>
            <select id="process-area-type" [(ngModel)]="selectedArea" [disabled]="analyzing()" (ngModelChange)="onAreaChanged()">
              <option value="civel">Processo cível</option>
              <option value="trabalhista">Processo trabalhista</option>
            </select>
            <small>Escolha a área para orientar a leitura. A IA não confirma automaticamente a competência judicial.</small>
          </div>

          @if (!workspace()) {
            <p class="hub-rail-intention"><strong>Objetivo da análise:</strong> {{goalLabel()}}<small>Você poderá acessar todas as áreas após o processamento.</small></p>
          }
          <label class="legal-upload-zone" [class.dragging]="isDragging()">
            <input
              type="file"
              #pdfUpload
              id="ai-ready-pdf-upload"
              accept="application/pdf,.pdf"
              multiple
              (change)="onFileInput($event)"
              (dragenter)="onDragEnter($event)"
              (dragover)="onDragOver($event)"
              (dragleave)="onDragLeave($event)"
              (drop)="onDrop($event)"
            />
            <span class="upload-symbol" aria-hidden="true">+</span>
            <strong>Adicionar PDFs</strong>
            <span>Arraste os documentos ou clique para selecionar</span>
            <small>Até {{ configuration()?.limite_arquivos ?? 12 }} arquivos · {{ configuration()?.limite_mb_por_arquivo ?? 25 }} MB por arquivo · {{ configuration()?.limite_total_mb ?? 80 }} MB no total</small>
          </label>

          <div class="selected-documents" aria-label="Documentos selecionados">
            @for (item of localDocuments(); track item.file.name + item.file.size) {
              <article class="selected-document">
                <button type="button" class="document-main" (click)="preview(item)">
                  <span class="pdf-badge">PDF</span>
                  <span class="document-copy">
                    <strong>{{ item.file.name }}</strong>
                    <small>{{ formatBytes(item.file.size) }}</small>
                  </span>
                </button>
                <button type="button" class="icon-button" aria-label="Remover documento" (click)="remove(item)">×</button>
              </article>
            }
          </div>

          <button class="primary analyze-button" type="button" [disabled]="!canAnalyze()" (click)="analyze()">
            @if (analyzing()) { Analisando documentos… } @else { Analisar processo }
          </button>

          <p class="privacy-note">Textos ficam em memória temporária no servidor. A análise utiliza o gerador corporativo; confira as regras de acesso e tratamento de dados antes do envio.</p>
        </aside>

        <section class="process-area">
          @if (workspace(); as result) {
            <div class="hub-action-bar surface">
              <div><span class="eyebrow">Dossiê em análise</span><strong>{{ result.tipo_processo === 'trabalhista' ? 'Justiça do Trabalho' : 'Área cível' }}</strong><small>Gerado em {{ result.gerado_em | date:'dd/MM/yyyy HH:mm' }} · valide sempre os autos</small></div>
              <div class="hub-actions"><button type="button" (click)="exportDossier()" title="Gerar resumo textual local no navegador">Exportar dossiê (.txt)</button><button type="button" (click)="exportReviewAgenda()" title="Baixar pauta para a reunião ou conferência jurídica">Pauta de revisão (.txt)</button><button type="button" class="hub-exit" (click)="endSession()" title="Limpar os PDFs e solicitar remoção do workspace">Encerrar sessão</button></div>
            </div>
            <div class="hub-quick-overview" aria-label="Acessos rápidos aos resultados">
              <button type="button" (click)="activeTab.set('cronologia')" class="hub-overview-action"><span class="hub-mini-identifier">01 / CRONOLOGIA</span><strong>{{result.linha_tempo.length}}</strong><small>Eventos identificados</small></button>
              <button type="button" (click)="activeTab.set('agenda')" class="hub-overview-action"><span class="hub-mini-identifier">02 / AGENDA</span><strong>{{result.agenda_documental.length}}</strong><small>Datas e compromissos citados</small></button>
              <button type="button" (click)="activeTab.set('provas')" class="hub-overview-action"><span class="hub-mini-identifier">03 / EVIDÊNCIAS</span><strong>{{result.provas_e_lacunas.length}}</strong><small>Provas e lacunas registradas</small></button>
              <button type="button" (click)="activeTab.set('documentos')" class="hub-overview-action"><span class="hub-mini-identifier">04 / QUALIDADE</span><strong>{{qualityReviewCount()}}</strong><small>PDFs com alertas de leitura</small></button>
            </div>
            <nav class="hub-tabs" aria-label="Seções do hub processual">
              @for (tab of hubTabs; track tab.id) {
                <button type="button" [class.active]="activeTab() === tab.id" [attr.aria-current]="activeTab() === tab.id ? 'page' : null" (click)="activeTab.set(tab.id)">
                  {{ tab.label }} @if (tab.id === 'agenda' && result.agenda_documental.length) { <span>{{ result.agenda_documental.length }}</span> }
                </button>
              }
            </nav>
            @if (activeTab() === 'panorama') {
            <section class="process-summary-grid">
              <article class="surface summary-card summary-card--wide">
                <div class="section-heading">
                  <div>
                    <span class="eyebrow">Resumo do processo</span>
                    <h2>{{ valueOrFallback(result.processo.numero_processo, 'Processo identificado nos autos') }}</h2>
                  </div>
                  <span class="status-chip">{{ valueOrFallback(result.processo.fase_processual, 'Fase não identificada') }}</span>
                </div>
                <p class="summary-text">{{ result.processo.resumo }}</p>
                <div class="case-meta-grid">
                  <div><small>Classe processual</small><strong>{{ valueOrFallback(result.processo.classe_processual) }}</strong></div>
                  <div><small>Assunto principal</small><strong>{{ valueOrFallback(result.processo.assunto_principal) }}</strong></div>
                  <div><small>Tribunal</small><strong>{{ valueOrFallback(result.processo.tribunal) }}</strong></div>
                  <div><small>Unidade judicial</small><strong>{{ valueOrFallback(result.processo.unidade_judicial) }}</strong></div>
                  <div><small>Valor da causa</small><strong>{{ valueOrFallback(result.processo.valor_causa) }}</strong></div>
                  <div><small>Última data relevante</small><strong>{{ valueOrFallback(result.processo.ultima_data_relevante) }}</strong></div>
                </div>
              </article>

              <article class="surface metric-card">
                <small>Documentos</small>
                <strong>{{ result.documentos.length }}</strong>
                <span>{{ totalPages() }} páginas no conjunto</span>
              </article>
              <article class="surface metric-card">
                <small>Fatos na linha do tempo</small>
                <strong>{{ result.linha_tempo.length }}</strong>
                <span>{{ highConfidenceEvents() }} com confiança alta</span>
              </article>
              <article class="surface metric-card">
                <small>Pontos de atenção</small>
                <strong>{{ result.processo.pontos_atencao.length }}</strong>
                <span>Itens para conferência jurídica</span>
              </article>
            </section>

            <section class="process-columns">
              <article class="surface timeline-panel">
                <div class="section-heading">
                  <div>
                    <span class="eyebrow">Cronologia</span>
                    <h2>Linha do tempo dos fatos</h2>
                  </div>
                  <span class="counter-badge">{{ result.linha_tempo.length }}</span>
                </div>
                @if (result.linha_tempo.length) {
                  <div class="timeline-list">
                    @for (event of result.linha_tempo; track event.documento + ':' + event.pagina + ':' + event.titulo) {
                      <article class="timeline-item">
                        <div class="timeline-rail"><span></span></div>
                        <div class="timeline-content">
                          <div class="timeline-topline">
                            <time>{{ event.data ?? 'Data não identificada' }}</time>
                            <span class="event-category">{{ categoryLabel(event.categoria) }}</span>
                          </div>
                          <h3>{{ event.titulo }}</h3>
                          <p>{{ event.descricao }}</p>
                          <div class="source-line">
                            <button class="hub-source" type="button" [disabled]="!event.pagina" (click)="openSource(event.documento, event.pagina)">{{ event.documento }}@if (event.pagina) { · p. {{ event.pagina }} }</button>
                            <span class="confidence" [attr.data-confidence]="event.confianca">{{ confidenceLabel(event.confianca) }}</span>
                          </div>
                        </div>
                      </article>
                    }
                  </div>
                } @else {
                  <p class="empty-inline">Nenhum evento temporal suficientemente claro foi identificado nos documentos.</p>
                }
              </article>

              <div class="insight-column">
                <article class="surface insight-panel">
                  <div class="section-heading"><div><span class="eyebrow">Leitura rápida</span><h2>Partes identificadas</h2></div></div>
                  @if (result.processo.partes.length) {
                    <div class="party-list">
                      @for (party of result.processo.partes; track party.nome + party.papel) {
                        <div><strong>{{ party.nome }}</strong><small>{{ party.papel }}</small></div>
                      }
                    </div>
                  } @else { <p class="empty-inline">Não identificadas com segurança.</p> }
                </article>

                <article class="surface insight-panel accent-panel">
                  <div class="section-heading"><div><span class="eyebrow">Conferência</span><h2>Pontos de atenção</h2></div></div>
                  <ul class="clean-list">
                    @for (item of result.processo.pontos_atencao; track item) { <li>{{ item }}</li> }
                    @empty { <li>Nenhum ponto específico foi destacado pela análise.</li> }
                  </ul>
                </article>

                <article class="surface insight-panel">
                  <div class="section-heading"><div><span class="eyebrow">Organização</span><h2>Próximas verificações</h2></div></div>
                  <ul class="clean-list numbered-list">
                    @for (item of result.processo.proximas_acoes_sugeridas; track item; let index = $index) {
                      <li><span>{{ index + 1 }}</span>{{ item }}</li>
                    }
                    @empty { <li><span>1</span>Revise os documentos originais antes de definir a estratégia processual.</li> }
                  </ul>
                </article>
              </div>
            </section>

            <section class="surface details-panel">
              <div class="section-heading">
                <div><span class="eyebrow">Conteúdo extraído</span><h2>Pedidos e fatos controvertidos</h2></div>
              </div>
              <div class="detail-columns">
                <div>
                  <h3>Pedidos identificados</h3>
                  <ul class="clean-list">
                    @for (item of result.processo.pedidos; track item) { <li>{{ item }}</li> }
                    @empty { <li>Nenhum pedido foi identificado com segurança.</li> }
                  </ul>
                </div>
                <div>
                  <h3>Fatos controvertidos</h3>
                  <ul class="clean-list">
                    @for (item of result.processo.fatos_controvertidos; track item) { <li>{{ item }}</li> }
                    @empty { <li>Nenhum fato controvertido foi explicitamente identificado.</li> }
                  </ul>
                </div>
              </div>
              <p class="ai-disclaimer">{{ result.aviso }}</p>
            </section>
            <section class="surface hub-content-panel hub-reading-guide">
              <div class="section-heading"><div><span class="eyebrow">Roteiro didático</span><h2>Como revisar um processo {{ result.tipo_processo === 'trabalhista' ? 'trabalhista' : 'cível' }}</h2></div></div>
              <div class="hub-guide-grid">
                @for (step of processGuide(result.tipo_processo); track step.title; let index = $index) {
                  <article><span>{{ index + 1 | number:'2.0' }}</span><h3>{{ step.title }}</h3><p>{{ step.description }}</p></article>
                }
              </div>
              <small class="hub-guide-note">Roteiro de organização, não substitui normas processuais, prazos oficiais ou a estratégia definida pelo advogado.</small>
            </section>
            }

            @if (activeTab() === 'cronologia') {
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Ordem temporal</span><h2>Movimentações e fatos documentados</h2></div><span class="counter-badge">{{ filteredTimeline().length }}</span></div>
                <div class="hub-toolbar"><label for="event-filter">Mostrar</label><select id="event-filter" [ngModel]="eventFilter()" (ngModelChange)="eventFilter.set($event)">
                  <option value="todos">Todos os eventos</option><option value="audiencia">Audiências</option><option value="decisao">Decisões</option><option value="manifestacao">Manifestações</option><option value="prova">Provas</option><option value="recurso">Recursos</option>
                </select></div>
                <div class="timeline-list">
                  @for (event of filteredTimeline(); track $index) {
                    <article class="timeline-item"><div class="timeline-rail"><span></span></div><div class="timeline-content">
                      <div class="timeline-topline"><time>{{ event.data || 'Data não informada' }}</time><span class="event-category">{{ categoryLabel(event.categoria) }}</span></div>
                      <h3>{{ event.titulo }}</h3><p>{{ event.descricao }}</p>
                      <button class="hub-source" type="button" [disabled]="!event.pagina" (click)="openSource(event.documento, event.pagina)">Consultar {{ event.documento }} · pág. {{ event.pagina || '?' }}</button>
                      <span class="confidence" [attr.data-confidence]="event.confianca">{{ confidenceLabel(event.confianca) }}</span>
                    </div></article>
                  } @empty {<p class="hub-empty">Não foram encontrados eventos para este filtro.</p>}
                </div>
              </section>
            }

            @if (activeTab() === 'agenda') {
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Agenda documental</span><h2>Audiências, intimações e prazos mencionados</h2></div><span class="counter-badge">{{ result.agenda_documental.length }}</span></div>
                <p class="hub-caution">As datas são extraídas do texto, não de um sistema de acompanhamento judicial. Não há cálculo de vencimento, contagem de prazo ou confirmação de intimação. Valide com o advogado responsável e no sistema oficial.</p>
                <div class="hub-item-grid">
                  @for (item of result.agenda_documental; track $index) {
                    <article class="hub-item-card">
                      <div class="hub-item-top"><span class="hub-kind">{{ agendaLabel(item.tipo) }}</span><span class="hub-review">A confirmar</span></div>
                      <h3>{{ item.titulo }}</h3><p>{{ item.descricao }}</p>
                      <strong class="hub-date">{{ item.data_mencionada || 'Sem data expressa' }}</strong>
                      <button class="hub-source" type="button" (click)="openSource(item.fonte.documento, item.fonte.pagina)">Abrir fonte · {{ item.fonte.documento }} · p. {{ item.fonte.pagina }}</button>
                    </article>
                  } @empty {<p class="hub-empty">Nenhuma audiência, comunicação ou data suficientemente referenciada foi identificada. Isso não significa ausência de prazos.</p>}
                </div>
              </section>
              <section class="surface hub-content-panel hub-checklist">
                <div class="section-heading"><div><span class="eyebrow">Plano de conferência</span><h2>Verificações operacionais sugeridas</h2></div></div>
                @for (task of result.processo.proximas_acoes_sugeridas; track $index; let index = $index) {
                  <label class="hub-task"><input type="checkbox" [checked]="checkedTasks().has(index)" (change)="toggleTask(index)"/><span>{{ task }}</span></label>
                } @empty {<p class="hub-empty">Confira a íntegra das publicações, movimentações e documentos diretamente no sistema processual.</p>}
                <small>Marcações são locais e temporárias: não substituem controle de tarefas, acompanhamento oficial ou registro de providências.</small>
              </section>
            }

            @if (activeTab() === 'provas') {
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Mapa de evidências</span><h2>Provas, divergências e lacunas para revisão</h2></div><span class="counter-badge">{{ result.provas_e_lacunas.length }}</span></div>
                <p class="hub-help">São hipóteses de organização documental, não conclusões sobre ônus da prova, procedência de pedidos ou risco jurídico.</p>
                <div class="hub-item-grid">
                  @for (item of result.provas_e_lacunas; track $index) {
                    <article class="hub-item-card"><span class="hub-kind" [attr.data-kind]="item.tipo">{{ evidenceLabel(item.tipo) }}</span><h3>{{ item.titulo }}</h3><p>{{ item.descricao }}</p>
                      <button class="hub-source" type="button" (click)="openSource(item.fonte.documento, item.fonte.pagina)">Conferir {{ item.fonte.documento }} · p. {{ item.fonte.pagina }}</button>
                    </article>
                  } @empty {<p class="hub-empty">Não há ocorrências com referência documental suficiente. Analise os PDFs originais antes de concluir que não existem divergências.</p>}
                </div>
              </section>
            }

            @if (activeTab() === 'documentos') {
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Biblioteca de autos</span><h2>Documentos e integridade textual</h2></div><span class="counter-badge">{{ result.documentos.length }}</span></div>
                <div class="hub-document-list">
                  @for (doc of result.documentos; track doc.identificador) {
                    <article class="hub-document"><span class="pdf-badge">PDF</span><div><strong>{{ doc.nome }}</strong><small>{{ doc.paginas_utilizaveis }} de {{ doc.paginas }} páginas com texto utilizável · Leitura {{ qualityLabel(doc.qualidade_textual) }}</small>
                      @for (warning of doc.alertas.slice(0, 3); track warning) {<small class="hub-warning">{{ warning }}</small>}
                    </div><button type="button" (click)="openSource(doc.nome, 1)">Visualizar</button></article>
                  }
                </div>
              </section>
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Busca verificável</span><h2>Localizar trechos nos autos</h2></div></div>
                <form class="hub-search" (submit)="onSearchSubmit($event)"><input name="docSearch" [(ngModel)]="searchDraft" maxlength="1600" placeholder="Ex.: audiência, horas extras, dano moral, sentença..." aria-label="Pesquisar trechos dos PDFs"/><button class="primary" type="submit" [disabled]="searching() || searchDraft.trim().length < 2">{{ searching() ? 'Buscando…' : 'Buscar' }}</button></form>
                <div class="hub-search-results">
                  @for (hit of searchHits(); track $index) {
                    <article class="hub-search-result"><button class="hub-source" type="button" (click)="openSource(hit.documento, hit.pagina)">{{ hit.documento }} · página {{ hit.pagina }}</button><p>{{ hit.trecho }}</p></article>
                  } @empty {<p class="hub-empty">{{ hasSearched() ? 'Nenhum trecho encontrado para esta consulta.' : 'Digite palavras-chave para procurar diretamente no texto dos PDFs.' }}</p>}
                </div>
              </section>
            }

            @if (activeTab() === 'perguntas') {
              <section class="surface hub-content-panel">
                <div class="section-heading"><div><span class="eyebrow">Pergunte aos autos</span><h2>Assistente contextual com fontes</h2></div></div>
                <p class="hub-help">Diferentemente do chat corporativo geral, este assistente pesquisa páginas dos PDFs deste processo e apresenta as fontes utilizadas. Respostas exigem revisão jurídica.</p>
                <div class="hub-suggested-questions">
                  @for (question of docketQuestions; track question) {<button type="button" (click)="askDocuments(question)" [disabled]="askingDocuments()">{{ question }}</button>}
                </div>
                <form class="hub-search" (submit)="onDocketQuestionSubmit($event)"><textarea name="docketQuestion" [(ngModel)]="questionDraft" rows="3" maxlength="1600" placeholder="Ex.: Onde está a decisão mais recente e o que foi determinado?" aria-label="Pergunta sobre os documentos"></textarea><button type="submit" class="primary" [disabled]="askingDocuments() || questionDraft.trim().length < 3 || !configuration()?.geracao_texto_configurada">{{ askingDocuments() ? 'Consultando…' : 'Perguntar' }}</button></form>
                @if (!configuration()?.geracao_texto_configurada) {<p class="hub-caution">Configure o gerador de texto corporativo para habilitar perguntas. A busca documental textual permanece disponível na aba Documentos.</p>}
                @if (docketAnswer(); as answer) {
                  <article class="hub-answer"><span class="eyebrow">Resposta assistida</span><p>{{ answer.resposta }}</p><small>{{ answer.aviso }}</small></article>
                  <h3 class="hub-reference-title">Páginas recuperadas para conferência</h3>
                  @for (hit of answer.fontes; track $index) {<article class="hub-search-result"><button class="hub-source" type="button" (click)="openSource(hit.documento, hit.pagina)">{{ hit.documento }} · página {{ hit.pagina }}</button><p>{{ hit.trecho }}</p></article>}
                } @else {<p class="hub-empty">Escolha uma pergunta acima ou escreva sua própria consulta.</p>}
              </section>
            }
          } @else {
            <div class="hub-home" aria-label="Página inicial de inteligência processual">
              <section class="hub-home-hero surface">
                <div class="hub-home-hero-copy">
                  <span class="eyebrow">COMECE POR AQUI</span>
                  <h2>Uma leitura mais clara dos autos começa com as fontes certas.</h2>
                  <p>Selecione PDFs do processo e escolha um objetivo. Após a análise, o painel abre diretamente a visão escolhida, com referências às páginas originais.</p>
                  <div class="hub-hero-actions">
                    <button class="primary" type="button" (click)="focusUpload()">Selecionar documentos <span aria-hidden="true">→</span></button>
                    <button type="button" (click)="selectGoal('perguntas')">Preparar perguntas aos autos</button>
                  </div>
                  <small>Sem exemplos fictícios, dados de tribunais ou processos pré-carregados. Os resultados aparecem somente depois do envio e da análise.</small>
                </div>
                <div class="hub-hero-visual" aria-hidden="true">
                  <div class="hub-visual-paper"><span class="hub-visual-label">AUTOS</span><i></i><i></i><i></i><i></i><div class="hub-visual-data"><b>01</b><b>02</b><b>03</b></div></div>
                  <div class="hub-visual-bubble"><span>FATOS</span><strong>Fontes → revisão</strong></div>
                </div>
              </section>

              <section class="hub-home-section" aria-labelledby="hub-objectives-title">
                <div class="hub-home-section-title"><div><span class="eyebrow">FLUXOS DE TRABALHO</span><h2 id="hub-objectives-title">O que você precisa analisar?</h2></div><small>Escolha um objetivo para abrir a área correspondente ao finalizar a leitura.</small></div>
                <div class="hub-objective-grid">
                  @for (shortcut of hubShortcuts; track shortcut.tab) {
                    <button type="button" class="hub-objective-card surface" [class.selected]="plannedTab() === shortcut.tab" [attr.aria-pressed]="plannedTab() === shortcut.tab" (click)="selectGoal(shortcut.tab)">
                      <span class="hub-objective-number">{{shortcut.number}} <span aria-hidden="true">↗</span></span>
                      <strong>{{shortcut.title}}</strong>
                      <span>{{shortcut.description}}</span>
                      <small>{{shortcut.outcome}}</small>
                    </button>
                  }
                </div>
              </section>

              <section class="hub-home-bottom-grid">
                <article class="surface hub-preflight" aria-labelledby="hub-preflight-title">
                  <div class="hub-home-section-title"><div><span class="eyebrow">PREPARAÇÃO</span><h2 id="hub-preflight-title">Checklist documental</h2></div><span class="hub-progress-count">{{preflightDoneCount()}}/{{preflightTasks().length}}</span></div>
                  <p>Use esta lista para organizar os arquivos antes da análise {{selectedArea === 'trabalhista' ? 'trabalhista' : 'cível'}}. Nenhum item é obrigatório para iniciar.</p>
                  <div class="hub-preflight-list">
                    @for (task of preflightTasks(); track task.id) {
                      <label class="hub-preflight-item"><input type="checkbox" [checked]="preflightChecked().has(task.id)" (change)="togglePreflight(task.id)"/>
                        <span><strong>{{task.title}}</strong><small>{{task.help}}</small></span></label>
                    }
                  </div>
                  <div class="hub-preflight-bottom"><span>Marcação local, não enviada à IA.</span><button type="button" (click)="clearPreflight()">Reiniciar checklist</button></div>
                </article>
                <article class="surface hub-next-steps" aria-labelledby="hub-steps-title">
                  <div class="hub-home-section-title"><div><span class="eyebrow">COMO FUNCIONA</span><h2 id="hub-steps-title">Da entrada à conferência</h2></div></div>
                  <ol class="hub-next-step-list">
                    <li><span>01</span><div><strong>Prepare os arquivos</strong><p>Confirme a área jurídica e selecione PDFs legíveis, respeitando o sigilo e as permissões de acesso.</p></div></li>
                    <li><span>02</span><div><strong>Escolha a pergunta central</strong><p>Priorize cronologia, provas, agenda, documentos ou consulta fundamentada aos autos.</p></div></li>
                    <li><span>03</span><div><strong>Valide e registre</strong><p>Confira as páginas citadas e exporte a pauta de revisão. Datas e conclusões exigem confirmação humana.</p></div></li>
                  </ol>
                  <div class="hub-home-disclaimer"><strong>Limite importante</strong><p>O hub não consulta sistemas de tribunais, não calcula prazos legais e não substitui análise jurídica ou controle processual oficial.</p></div>
                </article>
              </section>
              <section class="surface hub-home-questions" aria-labelledby="hub-home-questions-title">
                <div class="hub-home-section-title"><div><span class="eyebrow">PERGUNTAS ORIENTADORAS</span><h2 id="hub-home-questions-title">Comece com uma pergunta de revisão</h2></div><small>A pergunta escolhida será preenchida após a análise. Nenhuma consulta é enviada sem sua ação.</small></div>
                <div class="hub-home-question-grid">
                  @for (question of entryQuestions(); track question) {
                    <button type="button" [class.selected]="plannedQuestion() === question" (click)="prepareQuestion(question)"><span>{{question}}</span><span aria-hidden="true">↗</span></button>
                  }
                </div>
                @if (plannedQuestion()) {<p class="hub-question-confirmation" role="status">Pergunta preparada para a aba “Pergunte aos autos”. Ela será exibida para você revisar antes de enviar.</p>}
              </section>
            </div>
          }
        </section>
      </section>

      @if (previewDocument(); as previewItem) {
        <div class="preview-backdrop" (click)="closePreview()">
          <section class="preview-panel" role="dialog" aria-modal="true" aria-label="Visualização do PDF" (click)="$event.stopPropagation()">
            <header>
              <div><span class="eyebrow">Documento</span><strong>{{ previewItem.file.name }}</strong></div>
              <button type="button" class="icon-button" aria-label="Fechar PDF" (click)="closePreview()">×</button>
            </header>
            <iframe [src]="safePreviewUrl()" title="Documento PDF selecionado"></iframe>
          </section>
        </div>
      }

      <button
        type="button"
        class="chat-launcher"
        [class.open]="chatOpen()"
        (click)="toggleChat()"
        [attr.aria-expanded]="chatOpen()"
        aria-controls="ai-ready-chat-window"
        aria-label="Abrir assistente AI Ready"
      >
        <span>AI</span>
      </button>

      @if (chatOpen()) {
        <section id="ai-ready-chat-window" class="chat-window" aria-label="Assistente generativo AI Ready">
          <header class="chat-header">
            <div>
              <span class="chat-avatar">AI</span>
              <div><strong>Assistente corporativo geral</strong><small>Não consulta automaticamente os PDFs do workspace</small></div>
            </div>
            <button type="button" class="icon-button" aria-label="Fechar chat" (click)="toggleChat()">×</button>
          </header>

          <div class="chat-body">
            @if (!chatMessages().length) {
              <div class="chat-welcome">
                <strong>O que você quer perguntar?</strong>
                <p>Para perguntas sobre os arquivos enviados, use a aba "Pergunte aos autos". Este chat é independente e consulta o serviço corporativo geral.</p>
                <div class="suggestion-grid">
                  @for (question of suggestedQuestions; track question) {
                    <button type="button" [disabled]="!chatAvailable()" (click)="askSuggestion(question)">{{ question }}</button>
                  }
                </div>
              </div>
            }
            @for (message of chatMessages(); track $index) {
              <article class="chat-message" [class.user-message]="message.role === 'user'">
                <span>{{ message.role === 'user' ? 'Você' : 'AI Ready' }}</span>
                <p>{{ message.content }}</p>
                @if (message.referenceLabel) {
                  <small class="chat-message-reference">Referência enviada: {{ message.referenceLabel }}</small>
                }
              </article>
            }
            @if (chatLoading()) {
              <article class="chat-message typing-message"><span>AI Ready</span><p>Consultando a API corporativa…</p></article>
            }
          </div>

          <form class="chat-composer" (submit)="sendChat($event)">
            <div class="chat-context-controls" role="group" aria-label="Identificador de referência para a pergunta">
              <label for="chat-reference-type">
                <span>Tipo de identificador</span>
                <select id="chat-reference-type" name="chatReferenceType"
                  [(ngModel)]="chatReferenceType" [disabled]="chatLoading()"
                  (ngModelChange)="chatReferenceError.set('')">
                  @for (item of chatReferenceOptions; track item.value) {
                    <option [value]="item.value">{{ item.label }}</option>
                  }
                </select>
              </label>
              <label for="chat-reference-value">
                <span>Valor do identificador</span>
                <input id="chat-reference-value" name="chatReferenceValue" type="text"
                  [(ngModel)]="chatReferenceValue" [attr.maxlength]="maxChatReferenceLength"
                  placeholder="Informe o número" autocomplete="off" spellcheck="false"
                  [disabled]="chatLoading()" (ngModelChange)="chatReferenceError.set('')" />
              </label>
            </div>
            <small class="chat-context-hint">Preencha o valor para acrescentar automaticamente a referência à pergunta. Sem valor, a pergunta é enviada sem complemento.</small>
            @if (chatReferenceError()) {
              <p class="chat-context-error" role="alert">{{ chatReferenceError() }}</p>
            }
            <div class="chat-composer-row">
              <textarea
                [(ngModel)]="chatDraft"
                name="chatDraft"
                rows="2"
                maxlength="8000"
                [placeholder]="chatAvailable() ? 'Digite sua pergunta para o assistente…' : 'Chat corporativo não configurado'"
                [disabled]="!chatAvailable() || chatLoading()"
                (keydown.enter)="onChatEnter($event)"
              ></textarea>
              <button class="primary" type="submit" [disabled]="!chatAvailable() || !chatDraft.trim() || chatLoading()">Enviar</button>
            </div>
          </form>
        </section>
      }
    </main>
  `,
})
export class ChatbotPageComponent implements OnDestroy {
  private readonly api = inject(AiReadyApiService);
  private readonly notifications = inject(Notifications);
  private readonly sanitizer = inject(DomSanitizer);
  @ViewChild('pdfUpload') private pdfUpload?: ElementRef<HTMLInputElement>;

  readonly configuration = signal<AiReadyConfiguration | null>(null);
  readonly connectionState = signal<'checking' | 'online' | 'offline'>('checking');
  readonly localDocuments = signal<LocalDocument[]>([]);
  readonly workspace = signal<ProcessWorkspaceResponse | null>(null);
  readonly analyzing = signal(false);
  readonly isDragging = signal(false);
  readonly previewDocument = signal<LocalDocument | null>(null);
  readonly previewPage = signal(1);
  readonly activeTab = signal<HubTab>('panorama');
  readonly plannedTab = signal<HubTab>('panorama');
  readonly preflightChecked = signal<Set<string>>(new Set());
  readonly plannedQuestion = signal('');

  readonly eventFilter = signal<string>('todos');
  readonly checkedTasks = signal<Set<number>>(new Set());
  readonly searching = signal(false);
  readonly hasSearched = signal(false);
  readonly searchHits = signal<DocketSearchHit[]>([]);
  readonly askingDocuments = signal(false);
  readonly docketAnswer = signal<DocketAnswer | null>(null);
  selectedArea: 'civel' | 'trabalhista' = 'civel';
  searchDraft = '';
  questionDraft = '';
  readonly hubTabs: {id: HubTab; label: string}[] = [
    {id: 'panorama', label: 'Visão geral'}, {id: 'cronologia', label: 'Linha do tempo'},
    {id: 'agenda', label: 'Agenda e ações'}, {id: 'provas', label: 'Provas e lacunas'},
    {id: 'documentos', label: 'Documentos'}, {id: 'perguntas', label: 'Pergunte aos autos'},
  ];
  readonly hubShortcuts: HubShortcut[] = [
    {tab:'panorama',number:'01',title:'Visão estratégica',description:'Síntese factual, partes, pedidos e pontos de atenção.',outcome:'Abrir visão geral'},
    {tab:'cronologia',number:'02',title:'Linha do tempo',description:'Reconstrua a sequência dos eventos e localize sua origem.',outcome:'Abrir cronologia'},
    {tab:'agenda',number:'03',title:'Agenda documental',description:'Encontre datas e compromissos mencionados, sem calcular vencimentos.',outcome:'Abrir agenda e ações'},
    {tab:'provas',number:'04',title:'Mapa de evidências',description:'Organize provas mencionadas, divergências e lacunas.',outcome:'Abrir provas e lacunas'},
    {tab:'documentos',number:'05',title:'Busca de trechos',description:'Verifique qualidade da extração e pesquise palavras nos autos.',outcome:'Abrir documentos'},
    {tab:'perguntas',number:'06',title:'Pergunte aos autos',description:'Faça perguntas a partir dos PDFs e confira as páginas recuperadas.',outcome:'Abrir assistente contextual'},
  ];
  readonly entryQuestionsByArea: Record<'civel' | 'trabalhista', string[]> = {
    civel: [
      'Quais pedidos constam da inicial e onde estão descritos?',
      'Quais decisões estão documentadas e em que páginas?',
      'Quais fatos foram controvertidos pelas partes?',
      'Quais documentos são citados como prova de cada alegação?',
    ],
    trabalhista: [
      'Quais pedidos trabalhistas aparecem na reclamação?',
      'Em que páginas estão atas de audiência e depoimentos?',
      'Quais documentos mencionam jornada ou remuneração?',
      'Quais decisões e recursos constam dos autos anexados?',
    ],
  };
  readonly preflightByArea: Record<'civel' | 'trabalhista', PreflightItem[]> = {
    civel: [
      {id:'civel-inicial',title:'Petição inicial e pedidos',help:'Base para conhecer pretensões e fundamentos alegados.'},
      {id:'civel-defesa',title:'Contestação e manifestações',help:'Permite comparar narrativas e questões controvertidas.'},
      {id:'civel-decisoes',title:'Decisões e intimações',help:'Ajuda a reconstituir a tramitação e identificar datas mencionadas.'},
      {id:'civel-provas',title:'Documentos probatórios',help:'Identifique anexos que sustentam ou contrapõem alegações.'},
    ],
    trabalhista: [
      {id:'trabalhista-inicial',title:'Reclamação e defesa',help:'Delimita pedidos, narrativas e divergências alegadas.'},
      {id:'trabalhista-atas',title:'Atas e registros de audiência',help:'Fontes de manifestações, compromissos e deliberações.'},
      {id:'trabalhista-vinculo',title:'Documentos de trabalho',help:'Contratos, controles, recibos ou outros anexos, quando existentes.'},
      {id:'trabalhista-decisoes',title:'Decisões e recursos',help:'Reconstitui resultados registrados e próximos pontos de conferência.'},
    ],
  };
  readonly docketQuestions = [
    'Quais decisões estão documentadas e onde encontrá-las?',
    'Há audiência mencionada nos autos? Em qual página?',
    'Quais alegações e documentos tratam dos pedidos?',
  ];
  readonly chatOpen = signal(false);
  readonly chatLoading = signal(false);
  readonly chatMessages = signal<UiChatMessage[]>([]);
  chatDraft = '';
  readonly chatReferenceOptions = CHAT_REFERENCE_OPTIONS;
  readonly maxChatReferenceLength = MAX_CHAT_REFERENCE_LENGTH;
  readonly chatReferenceError = signal('');
  chatReferenceType: ChatReferenceType = 'gcpj';
  chatReferenceValue = '';

  readonly suggestedQuestions = [
    'Como organizar a leitura de uma sentença judicial?',
    'Que informações conferir em uma ata de audiência?',
    'Como diferenciar alegações de evidências documentais?',
    'Quais cuidados tomar ao resumir uma decisão?',
  ];

  readonly selectedFiles = computed(() => this.localDocuments().map(item => item.file));
  readonly canAnalyze = computed(() => this.selectedFiles().length > 0 && !this.analyzing() && Boolean(this.configuration()?.geracao_texto_configurada));
  readonly chatAvailable = computed(() => Boolean(this.configuration()?.chat_qa_configurado));
  readonly totalPages = computed(() => this.workspace()?.documentos.reduce((sum, item) => sum + item.paginas, 0) ?? 0);
  readonly filteredTimeline = computed(() => {
    const events = this.workspace()?.linha_tempo ?? [];
    return this.eventFilter() === 'todos' ? events : events.filter(event => event.categoria === this.eventFilter());
  });
  readonly highConfidenceEvents = computed(() => this.workspace()?.linha_tempo.filter(item => item.confianca === 'alta').length ?? 0);
  readonly qualityReviewCount = computed(() => this.workspace()?.documentos.filter(item => item.qualidade_textual !== 'boa' || item.alertas.length > 0).length ?? 0);

  readonly connectionLabel = computed(() => this.connectionState() === 'online' ? 'IA corporativa disponível' : this.connectionState() === 'checking' ? 'Verificando conexão' : 'IA indisponível');
  readonly connectionDetail = computed(() => {
    if (this.connectionState() === 'checking') return 'Validando backend e configuração';
    if (this.connectionState() === 'offline') return 'Revise a configuração das APIs corporativas';
    const analysis = this.configuration()?.geracao_texto_configurada ? 'análise documental ativa' : 'análise documental indisponível';
    const chat = this.configuration()?.chat_qa_configurado ? 'chat Q&A ativo' : 'chat Q&A indisponível';
    return `${analysis} · ${chat}`;
  });

  constructor() {
    void this.checkConnection();
  }

  ngOnDestroy(): void {
    this.localDocuments().forEach(item => URL.revokeObjectURL(item.url));
    const workspaceId = this.workspace()?.workspace_id;
    if (workspaceId) this.api.discard(workspaceId).subscribe({error: () => undefined});
  }

  async checkConnection(): Promise<void> {
    this.connectionState.set('checking');
    try {
      const [health, configuration] = await Promise.all([
        firstValueFrom(this.api.health()),
        firstValueFrom(this.api.configuration()),
      ]);
      if (health.status !== 'ok' || health.versao_api !== '3.0.0') throw new Error('O frontend e o backend não estão na mesma versão.');
      this.configuration.set(configuration);
      this.connectionState.set(configuration.geracao_texto_configurada || configuration.chat_qa_configurado ? 'online' : 'offline');
    } catch (error) {
      this.connectionState.set('offline');
      this.notifications.error(error);
    }
  }

  entryQuestions(): string[] { return this.entryQuestionsByArea[this.selectedArea]; }

  prepareQuestion(question: string): void {
    // Guarda somente a intenção local; nenhuma requisição é disparada neste momento.
    if (!this.entryQuestions().includes(question)) return;
    this.plannedQuestion.set(question);
    this.selectGoal('perguntas');
  }

  preflightTasks(): PreflightItem[] { return this.preflightByArea[this.selectedArea]; }

  preflightDoneCount(): number {
    return this.preflightTasks().filter(task => this.preflightChecked().has(task.id)).length;
  }

  togglePreflight(id: string): void {
    const visibleIds = this.preflightTasks().map(task => task.id);
    if (!visibleIds.includes(id)) return;
    const updated = new Set(this.preflightChecked());
    if (updated.has(id)) updated.delete(id); else updated.add(id);
    this.preflightChecked.set(updated);
  }

  clearPreflight(): void { this.preflightChecked.set(new Set()); }

  onAreaChanged(): void {
    // A mudança de área não apaga documentos; só reinicia o checklist orientativo.
    this.clearPreflight();
    this.plannedQuestion.set('');
  }

  goalLabel(): string {
    return this.hubShortcuts.find(item => item.tab === this.plannedTab())?.title ?? 'Visão estratégica';
  }

  selectGoal(tab: HubTab): void {
    this.plannedTab.set(tab);
    if (this.workspace()) this.activeTab.set(tab);
  }

  focusUpload(): void {
    // A seleção é iniciada pelo usuário: nunca envia arquivos automaticamente.
    this.pdfUpload?.nativeElement.click();
  }

  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.addFiles(Array.from(input.files ?? []));
    input.value = '';
  }

  onDragEnter(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(true);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
    this.isDragging.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging.set(false);
    this.addFiles(Array.from(event.dataTransfer?.files ?? []));
  }

  private addFiles(files: File[]): void {
    const limit = this.configuration()?.limite_arquivos ?? 12;
    const maxBytes = (this.configuration()?.limite_mb_por_arquivo ?? 25) * 1024 * 1024;
    const maxTotalBytes = (this.configuration()?.limite_total_mb ?? 80) * 1024 * 1024;
    const current = [...this.localDocuments()];
    for (const file of files) {
      if (!file.name.toLowerCase().endsWith('.pdf') || !['application/pdf', ''].includes(file.type)) {
        this.notifications.show(`${file.name}: envie somente arquivos PDF.`, 'error');
        continue;
      }
      if (file.size > maxBytes) {
        this.notifications.show(`${file.name}: arquivo acima do limite permitido.`, 'error');
        continue;
      }
      if (current.some(item => item.file.name.toLowerCase() === file.name.toLowerCase())) {
        this.notifications.show(`${file.name}: já existe um PDF com esse nome. Renomeie para manter as fontes identificáveis.`, 'error');
        continue;
      }
      const totalAfterAdd = current.reduce((sum, item) => sum + item.file.size, 0) + file.size;
      if (totalAfterAdd > maxTotalBytes) {
        this.notifications.show(`O conjunto selecionado excede o limite total de ${Math.round(maxTotalBytes / (1024 * 1024))} MB.`, 'error');
        break;
      }
      if (current.length >= limit) {
        this.notifications.show(`O limite atual é de ${limit} arquivos por análise.`, 'error');
        break;
      }
      current.push({file, url: URL.createObjectURL(file)});
    }
    this.localDocuments.set(current);
  }

  remove(item: LocalDocument): void {
    URL.revokeObjectURL(item.url);
    this.localDocuments.update(items => items.filter(candidate => candidate !== item));
    if (this.previewDocument() === item) this.previewDocument.set(null);
  }

  async analyze(): Promise<void> {
    if (!this.canAnalyze()) return;
    this.analyzing.set(true);
    const previousWorkspaceId = this.workspace()?.workspace_id;
    try {
      const result = await firstValueFrom(this.api.analyze(this.selectedFiles(), this.selectedArea));
      this.workspace.set(result);
      this.activeTab.set(this.plannedTab());
      this.questionDraft = this.plannedQuestion();
      this.checkedTasks.set(new Set());
      this.searchHits.set([]);
      this.hasSearched.set(false);
      this.docketAnswer.set(null);
      if (previousWorkspaceId && previousWorkspaceId !== result.workspace_id) {
        this.api.discard(previousWorkspaceId).subscribe({error: () => undefined});
      }
      this.notifications.show('Processo analisado. Revise a síntese e as referências nos autos.');
    } catch (error) {
      this.notifications.error(error);
    } finally {
      this.analyzing.set(false);
    }
  }

  endSession(): void {
    // Apaga imediatamente a interface e solicita exclusão dos dados em memória no backend.
    const id = this.workspace()?.workspace_id;
    if (id) this.api.discard(id).subscribe({error: () => this.notifications.show('Não foi possível confirmar a exclusão no servidor. O workspace expirará conforme o TTL configurado.', 'error')});
    this.localDocuments().forEach(item => URL.revokeObjectURL(item.url));
    this.localDocuments.set([]);
    this.workspace.set(null);
    this.previewDocument.set(null);
    this.checkedTasks.set(new Set());
    this.searchHits.set([]);
    this.hasSearched.set(false);
    this.docketAnswer.set(null);
    this.chatMessages.set([]);
    this.questionDraft = '';
    this.searchDraft = '';
    this.chatDraft = '';
    this.chatReferenceType = 'gcpj';
    this.chatReferenceValue = '';
    this.chatReferenceError.set('');
    this.activeTab.set('panorama');
    this.plannedTab.set('panorama');
    this.plannedQuestion.set('');
    this.clearPreflight();
  }

  preview(item: LocalDocument): void {
    this.previewPage.set(1);
    this.previewDocument.set(item);
  }

  openSource(filename: string, page: number | null): void {
    const item = this.localDocuments().find(candidate => candidate.file.name === filename);
    if (!item) {
      this.notifications.show('PDF de origem não está mais disponível nesta seleção.', 'error');
      return;
    }
    this.previewPage.set(page && Number.isInteger(page) && page > 0 ? page : 1);
    this.previewDocument.set(item);
  }

  closePreview(): void {
    this.previewDocument.set(null);
  }

  safePreviewUrl(): SafeResourceUrl {
    const url = this.previewDocument()?.url ? `${this.previewDocument()!.url}#page=${this.previewPage()}` : 'about:blank';
    // A URL foi criada localmente a partir do File selecionado pelo próprio usuário.
    return this.sanitizer.bypassSecurityTrustResourceUrl(url);
  }

  toggleChat(): void {
    // O chat é independente do workspace local de PDFs e consulta a API Q&A corporativa.
    this.chatOpen.set(!this.chatOpen());
  }

  askSuggestion(question: string): void {
    this.chatDraft = question;
    void this.submitChat();
  }

  sendChat(event: SubmitEvent): void {
    event.preventDefault();
    void this.submitChat();
  }

  onChatEnter(event: Event): void {
    const keyboardEvent = event as KeyboardEvent;
    if (keyboardEvent.shiftKey) return;
    keyboardEvent.preventDefault();
    void this.submitChat();
  }

  private async submitChat(): Promise<void> {
    const question = this.chatDraft.trim();
    if (!this.chatAvailable() || !question || this.chatLoading()) return;

    // Captura o contexto no momento do envio; alterar os campos depois não modifica a solicitação anterior.
    const referenceType = this.chatReferenceType;
    const referenceValue = this.chatReferenceValue.trim();
    let outgoingPrompt: string;
    try {
      outgoingPrompt = buildContextualChatPrompt(question, referenceType, referenceValue);
      this.chatReferenceError.set('');
    } catch (error) {
      this.chatReferenceError.set(error instanceof Error ? error.message : 'Identificador inválido.');
      return;
    }

    const referenceOption = this.chatReferenceOptions.find(item => item.value === referenceType);
    const referenceLabel = referenceValue && referenceOption ? `${referenceOption.label}: ${referenceValue}` : undefined;
    this.chatMessages.update(items => [...items, {role: 'user', content: question, referenceLabel}]);
    this.chatDraft = '';
    this.chatLoading.set(true);
    try {
      const response = await firstValueFrom(this.api.chat(outgoingPrompt));
      this.chatMessages.update(items => [...items, {role: 'assistant', content: response.resposta}]);
    } catch (error) {
      this.notifications.error(error);
      this.chatMessages.update(items => [...items, {role: 'assistant', content: 'Não foi possível consultar a API de perguntas e respostas agora. Verifique a conexão e tente novamente.'}]);
    } finally {
      this.chatLoading.set(false);
    }
  }

  processGuide(area: 'civel' | 'trabalhista'): {title: string; description: string}[] {
    // O roteiro organiza a análise documental, sem prescrever enquadramento legal.
    return area === 'trabalhista' ? [
      {title: 'Identifique pedidos e defesa', description: 'Diferencie pedidos formulados, alegações de cada parte e documentos relacionados.'},
      {title: 'Organize os documentos de trabalho', description: 'Localize referências a jornada, remuneração, vínculo e demais fatos efetivamente discutidos no processo.'},
      {title: 'Confira audiências e decisões', description: 'Verifique atas, intimações, decisões e eventual fase de apuração diretamente no sistema judicial.'},
    ] : [
      {title: 'Delimite as controvérsias', description: 'Organize as pretensões, os argumentos apresentados e as provas citadas nos autos.'},
      {title: 'Reconstitua a tramitação', description: 'Confira decisões, manifestações e intimações, distinguindo fatos de interpretações.'},
      {title: 'Planeje a revisão jurídica', description: 'Use fontes e páginas para preparar a conferência das providências pelo advogado responsável.'},
    ];
  }

  agendaLabel(kind: string): string {
    return ({audiencia: 'Audiência', prazo_mencionado: 'Prazo citado', intimacao: 'Intimação', pericia: 'Perícia', outro: 'Outro evento'} as Record<string, string>)[kind] ?? 'Evento';
  }

  evidenceLabel(kind: string): string {
    return ({prova: 'Prova mencionada', divergencia: 'Divergência a conferir', lacuna: 'Lacuna documental'} as Record<string, string>)[kind] ?? kind;
  }

  qualityLabel(value: string): string {
    return ({boa: 'boa', parcial: 'parcial', insuficiente: 'insuficiente'} as Record<string, string>)[value] ?? value;
  }

  toggleTask(index: number): void {
    const updated = new Set(this.checkedTasks());
    if (updated.has(index)) updated.delete(index); else updated.add(index);
    this.checkedTasks.set(updated);
  }

  onSearchSubmit(event: Event): void {
    event.preventDefault();
    void this.searchDocuments();
  }

  async searchDocuments(): Promise<void> {
    const id = this.workspace()?.workspace_id;
    const query = this.searchDraft.trim();
    if (!id || query.length < 2 || this.searching()) return;
    this.searching.set(true);
    try {
      const response = await firstValueFrom(this.api.search(id, query));
      this.searchHits.set(response.resultados);
      this.hasSearched.set(true);
    } catch (error) {
      this.notifications.error(error);
      this.searchHits.set([]);
    } finally {
      this.searching.set(false);
    }
  }

  onDocketQuestionSubmit(event: Event): void {
    event.preventDefault();
    void this.askDocuments(this.questionDraft);
  }

  async askDocuments(question: string): Promise<void> {
    const id = this.workspace()?.workspace_id;
    const query = question.trim();
    if (!id || query.length < 3 || this.askingDocuments() || !this.configuration()?.geracao_texto_configurada) return;
    this.questionDraft = query;
    this.askingDocuments.set(true);
    this.docketAnswer.set(null);
    try {
      this.docketAnswer.set(await firstValueFrom(this.api.askDocuments(id, query)));
    } catch (error) {
      this.notifications.error(error);
    } finally {
      this.askingDocuments.set(false);
    }
  }

  exportReviewAgenda(): void {
    const result = this.workspace();
    if (!result) return;
    // Relatório local de preparação. Datas e referências exigem confirmação oficial.
    const lines = [
      'PAUTA DE REVISÃO JURÍDICA — CONFERIR NOS AUTOS',
      `Área informada: ${result.tipo_processo}`,
      `Processo: ${result.processo.numero_processo || 'não identificado'}`,
      `Documento gerado em: ${new Date().toISOString()}`,
      '', '1. DOCUMENTOS COM ALERTAS DE EXTRAÇÃO:',
      ...result.documentos.filter(item => item.qualidade_textual !== 'boa' || item.alertas.length).map(item => `- ${item.nome}: ${item.qualidade_textual}; ${item.alertas.join('; ') || 'revisar qualidade'}`),
      '', '2. DATAS E EVENTOS PARA VALIDAÇÃO:',
      ...result.agenda_documental.map(item => `- [ ] ${item.titulo} | ${item.data_mencionada || 'data não identificada'} | ${item.fonte.documento} p. ${item.fonte.pagina}`),
      '', '3. PONTOS DE ATENÇÃO:',
      ...result.processo.pontos_atencao.map(item => `- [ ] ${item}`),
      '', '4. PROVAS, LACUNAS E DIVERGÊNCIAS:',
      ...result.provas_e_lacunas.map(item => `- [ ] ${item.tipo}: ${item.titulo} | ${item.fonte.documento} p. ${item.fonte.pagina}`),
      '', '5. PROVIDÊNCIAS SUGERIDAS PARA REVISÃO:',
      ...result.processo.proximas_acoes_sugeridas.map(item => `- [ ] ${item}`),
      '', '6. CONFERÊNCIA FINAL:',
      '- [ ] Conferir íntegra dos documentos e páginas citadas',
      '- [ ] Validar intimações e eventual prazo no sistema oficial',
      '- [ ] Registrar responsáveis e providências no sistema institucional',
      '', result.aviso,
      'Este relatório não confirma vencimentos, atos processuais ou avaliações jurídicas.',
    ];
    this.downloadText(lines, 'pauta-revisao-processual');
  }

  private downloadText(lines: string[], filename: string): void {
    const file = new Blob([lines.join('\n')], {type: 'text/plain;charset=utf-8'});
    const url = URL.createObjectURL(file);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${filename}-${new Date().toISOString().slice(0, 10)}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  }

  exportDossier(): void {
    const result = this.workspace();
    if (!result) return;
    // A exportação somente ocorre mediante ação explícita e não envia conteúdo a terceiros.
    const lines = [
      'HUB DE INTELIGÊNCIA PROCESSUAL — DOSSÊ DE CONFERÊNCIA',
      `Área declarada: ${result.tipo_processo}`,
      `Gerado em: ${result.gerado_em}`,
      `Processo: ${result.processo.numero_processo || 'não identificado'}`,
      `Classe: ${result.processo.classe_processual || 'não identificada'}`,
      `Resumo: ${result.processo.resumo}`,
      '', 'PEDIDOS:', ...result.processo.pedidos.map(item => `- ${item}`),
      '', 'EVENTOS:', ...result.linha_tempo.map(item => `- ${item.data || 'sem data'} | ${item.titulo} | ${item.documento} p. ${item.pagina ?? '?'}`),
      '', 'AGENDA MENCIONADA NOS AUTOS — PRAZOS NÃO CALCULADOS:',
      ...result.agenda_documental.map(item => `- ${item.titulo} | ${item.data_mencionada || 'sem data'} | ${item.fonte.documento} p. ${item.fonte.pagina}`),
      '', 'PROVAS E LACUNAS:', ...result.provas_e_lacunas.map(item => `- ${item.tipo}: ${item.titulo} | ${item.fonte.documento} p. ${item.fonte.pagina}`),
      '', 'PONTOS DE ATENÇÃO:', ...result.processo.pontos_atencao.map(item => `- ${item}`),
      '', 'VERIFICAÇÕES OPERACIONAIS:', ...result.processo.proximas_acoes_sugeridas.map(item => `- ${item}`),
      '', result.aviso, 'Não substitui consulta ao tribunal, controle de prazos ou parecer do advogado.',
    ];
    this.downloadText(lines, 'dossie-processual');
  }

  valueOrFallback(value: string | null | undefined, fallback = 'Não identificado'): string {
    return value?.trim() || fallback;
  }

  formatBytes(bytes: number): string {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  categoryLabel(category: TimelineEvent['categoria']): string {
    const labels: Record<TimelineEvent['categoria'], string> = {
      ajuizamento: 'Ajuizamento', citacao: 'Citação', manifestacao: 'Manifestação', prova: 'Prova', audiencia: 'Audiência',
      decisao: 'Decisão', recurso: 'Recurso', cumprimento: 'Cumprimento', outro: 'Outro',
    };
    return labels[category];
  }

  confidenceLabel(confidence: TimelineEvent['confianca']): string {
    return confidence === 'alta' ? 'Confiança alta' : confidence === 'media' ? 'Confiança média' : 'Revisar fonte';
  }
}
