/** Menu único: página inicial, BJN, auditoria e chatbot preservam a linguagem visual. */
import { Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { NotificationsComponent } from './shared/notifications.component';
import { APPLICATIONS, applicationForUrl } from './core/application-registry';
import type { ApplicationDescriptor } from './core/application-registry';
import { NotificationsComponent as AuditNotificationsComponent } from './auditoria/shared/notifications.component';


@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterLink, RouterLinkActive, RouterOutlet, NotificationsComponent, AuditNotificationsComponent],
  template: `
    <div class="application-shell" [class.nav-collapsed]="navigationCollapsed()" [class.module-audit]="isAudit()">
      <aside class="platform-sidebar" [class.collapsed]="navigationCollapsed()" aria-label="Aplicações do ecossistema jurídico">
        <div class="platform-sidebar-header">
          <button type="button" class="sidebar-toggle global-toggle" (click)="toggleNavigation()"
            [attr.aria-expanded]="!navigationCollapsed()" aria-controls="platform-nav"
            aria-label="Expandir ou retrair menu">☰</button>
          @if (!navigationCollapsed()) {
            <a class="platform-branding" routerLink="/" aria-label="Voltar à página inicial">
              <span class="brand-mark" aria-hidden="true"></span>
              <span><strong>Ecossistema jurídico</strong><small>Soluções inteligentes</small></span>
            </a>
          }
        </div>
        <nav id="platform-nav" class="platform-nav">
          @for (application of applications; track application.key) {
            <a [routerLink]="application.route" routerLinkActive="active"
              [routerLinkActiveOptions]="{exact: application.key === 'home'}" class="platform-link"
              [attr.title]="application.label">
              <span class="platform-link-badge" aria-hidden="true">{{application.badge}}</span>
              @if (!navigationCollapsed()) {
                <span class="platform-link-copy"><strong>{{application.label}}</strong><small>{{application.subtitle}}</small></span>
              }
            </a>
          }
        </nav>
        @if (!navigationCollapsed()) {
          <div class="sidebar-footnote"><span class="sidebar-footnote-dot"></span> Ambiente jurídico integrado</div>
        }
      </aside>
      <div class="application-content-shell">
        <header class="application-bar">
          <div class="application-bar-main">
            <a class="brand brand--app" [routerLink]="activeApplication().route" [attr.aria-label]="'Ir para ' + activeApplication().label">
              <span class="brand-mark" aria-hidden="true"></span>
              <span class="brand-copy"><small>{{isHome() ? 'Portal' : 'Aplicação'}}</small><strong>{{activeApplication().label}}</strong></span>
            </a>
            @if (isAudit()) {
              <nav aria-label="Seções da auditoria" class="top-level-nav top-level-nav--bjn">
                <a routerLink="/auditoria-pagamentos/calculo" routerLinkActive="context-active">Cálculo</a>
                <a routerLink="/auditoria-pagamentos/historico" routerLinkActive="context-active">Histórico</a>
                <a routerLink="/auditoria-pagamentos/qualidade-ia" routerLinkActive="context-active">Qualidade IA</a>
                <a routerLink="/auditoria-pagamentos/lotes" routerLinkActive="context-active">Lotes</a>
                <a routerLink="/auditoria-pagamentos/indices" routerLinkActive="context-active">Índices</a>
              </nav>
            }
            @if (activeApplication().key === 'bjn') {
              <nav aria-label="Seções BJN" class="top-level-nav top-level-nav--bjn">
                <a routerLink="/bjn" routerLinkActive="context-active" [routerLinkActiveOptions]="{exact:true}">Minutas</a>
                <a routerLink="/bjn/demandas" routerLinkActive="context-active">Demandas</a>
                <a routerLink="/bjn/demandas/nova" class="top-new-demand">+ Nova demanda</a>
              </nav>
            }
            @if (activeApplication().key === 'behavior') {
              <nav aria-label="Seções Behavior" class="top-level-nav top-level-nav--context">
                <span>Agentes sintéticos</span><span>Cenários e eventos</span><span>Experimentos</span>
              </nav>
            }
            @if (activeApplication().key === 'chatbot') {
              <nav aria-label="Recursos do chatbot" class="top-level-nav top-level-nav--context">
                <span>Processos cíveis e trabalhistas</span><span>Agenda e evidências</span><span>Perguntas aos autos</span>
              </nav>
            }
          </div>
          <a class="top-home-link" routerLink="/" [attr.aria-label]="'Página inicial'">Página inicial</a>
        </header>
        <app-notifications />
        <app-audit-notifications />
        <div class="route-content"><router-outlet /></div>
      </div>
    </div>
  `,
})
export class AppComponent {
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  readonly navigationCollapsed = signal(false);
  readonly currentUrl = signal(this.router.url);
  readonly applications: readonly ApplicationDescriptor[] = APPLICATIONS;
  readonly activeApplication = computed<ApplicationDescriptor>(() => applicationForUrl(this.currentUrl()));
  readonly isAudit = computed(() => this.activeApplication().key === 'auditoria');
  readonly isHome = computed(() => this.activeApplication().key === 'home');
  constructor() {
    this.router.events.pipe(filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef)).subscribe(event => this.currentUrl.set(event.urlAfterRedirects));
  }
  toggleNavigation(): void { this.navigationCollapsed.set(!this.navigationCollapsed()); }
}
