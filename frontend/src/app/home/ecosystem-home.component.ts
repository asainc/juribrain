/** Página institucional com acessos efetivos, sem métricas operacionais fictícias. */
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { APPLICATIONS } from '../core/application-registry';
@Component({
  selector: 'app-ecosystem-home', standalone: true, imports: [RouterLink],
  template: `
    <main class="ecosystem-home">
      <div class="ecosystem-container">
        <section class="ecosystem-intro">
          <div class="ecosystem-intro-copy">
            <span class="eyebrow ecosystem-kicker"><span class="kicker-line"></span> PLATAFORMA JURÍDICA</span>
            <h1>Um ecossistema.<br><span>Novas possibilidades</span> para o jurídico.</h1>
            <p>Quatro soluções em um só lugar. Acesse ferramentas para minutas, auditoria, inteligência processual e simulação multiagente com uma experiência integrada.</p>
            <a routerLink="/bjn" class="ecosystem-primary-action">Explorar soluções <span aria-hidden="true">→</span></a>
          </div>
          <div class="ecosystem-hero-visual" aria-hidden="true">
            <div class="hero-decoration hero-decoration--top"></div>
            <div class="hero-decoration hero-decoration--bottom"></div>
            <div class="hero-main-card"><div class="hero-main-icon"><span></span><span></span><span></span></div><div class="hero-main-copy"><span>ECOSSISTEMA</span><strong>Jurídico</strong><small>Uma experiência conectada</small></div></div>
            <div class="hero-small-card hero-small-card--first"><span class="hero-glyph">BJ</span><span>Minutas e demandas</span></div>
            <div class="hero-small-card hero-small-card--second"><span class="hero-glyph">AP</span><span>Auditoria e cálculos</span></div>
            <div class="hero-small-card hero-small-card--third"><span class="hero-glyph">IA</span><span>Inteligência processual</span></div>
          </div>
        </section>
        <section class="ecosystem-solutions" aria-labelledby="solutions-heading">
          <div class="ecosystem-section-heading"><div><span class="eyebrow">NOSSAS SOLUÇÕES</span><h2 id="solutions-heading">Escolha por onde começar</h2><p>Todos os módulos estão disponíveis no mesmo menu.</p></div><span class="ecosystem-section-count">{{solutions.length.toString().padStart(2, '0')}} aplicações</span></div>
          <div class="ecosystem-cards">
            @for (application of solutions; track application.key) {
              <a [routerLink]="application.route" class="ecosystem-app-card">
                <div class="ecosystem-card-top"><span class="ecosystem-card-icon">{{application.badge}}</span><span class="ecosystem-card-arrow" aria-hidden="true">↗</span></div>
                <span class="ecosystem-card-category">{{application.category}}</span><h3>{{application.label}}</h3>
                <p>{{application.description}}</p>
                <span class="ecosystem-card-footer">Acessar aplicação <span aria-hidden="true">→</span></span>
              </a>
            }
          </div>
        </section>
        <footer class="ecosystem-footer"><span>Ecossistema jurídico · Aplicações integradas</span><span>As recomendações de IA exigem revisão humana.</span></footer>
      </div>
    </main>
  `,
})
export class EcosystemHomeComponent {
  readonly solutions = APPLICATIONS.filter(application => application.key !== "home");
}
