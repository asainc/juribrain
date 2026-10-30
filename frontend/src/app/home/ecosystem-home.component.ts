/** Página institucional com acessos efetivos, sem métricas operacionais fictícias. */
import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
@Component({
  selector: 'app-ecosystem-home', standalone: true, imports: [RouterLink],
  template: `
    <main class="ecosystem-home">
      <div class="ecosystem-container">
        <section class="ecosystem-intro">
          <div class="ecosystem-intro-copy">
            <span class="eyebrow ecosystem-kicker"><span class="kicker-line"></span> PLATAFORMA JURÍDICA</span>
            <h1>Um ecossistema.<br><span>Novas possibilidades</span> para o jurídico.</h1>
            <p>Três soluções em um só lugar. Acesse ferramentas de geração de minutas, auditoria de pagamentos e inteligência processual com uma experiência integrada.</p>
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
          <div class="ecosystem-section-heading"><div><span class="eyebrow">NOSSAS SOLUÇÕES</span><h2 id="solutions-heading">Escolha por onde começar</h2><p>Todos os módulos estão disponíveis no mesmo menu.</p></div><span class="ecosystem-section-count">03 aplicações</span></div>
          <div class="ecosystem-cards">
            <a routerLink="/bjn" class="ecosystem-app-card">
              <div class="ecosystem-card-top"><span class="ecosystem-card-icon">BJ</span><span class="ecosystem-card-arrow" aria-hidden="true">↗</span></div>
              <span class="ecosystem-card-category">GESTÃO JURÍDICA</span><h3>BJN</h3>
              <p>Crie minutas a partir do catálogo de cláusulas e gerencie demandas, análises e pareceres jurídicos.</p>
              <span class="ecosystem-card-footer">Acessar aplicação <span aria-hidden="true">→</span></span>
            </a>
            <a routerLink="/auditoria-pagamentos/calculo" class="ecosystem-app-card">
              <div class="ecosystem-card-top"><span class="ecosystem-card-icon">AP</span><span class="ecosystem-card-arrow" aria-hidden="true">↗</span></div>
              <span class="ecosystem-card-category">CONFERÊNCIA FINANCEIRA</span><h3>Auditoria de Pagamentos</h3>
              <p>Consulte documentos, execute cálculos judiciais e acompanhe histórico, lotes, índices e qualidade da IA.</p>
              <span class="ecosystem-card-footer">Acessar aplicação <span aria-hidden="true">→</span></span>
            </a>
            <a routerLink="/chatbot" class="ecosystem-app-card">
              <div class="ecosystem-card-top"><span class="ecosystem-card-icon">IA</span><span class="ecosystem-card-arrow" aria-hidden="true">↗</span></div>
              <span class="ecosystem-card-category">INTELIGÊNCIA ARTIFICIAL</span><h3>Chatbot / AI Ready</h3>
              <p>Explore processos cíveis e trabalhistas com agenda documental, provas, busca nos PDFs e respostas com fontes.</p>
              <span class="ecosystem-card-footer">Acessar aplicação <span aria-hidden="true">→</span></span>
            </a>
          </div>
        </section>
        <footer class="ecosystem-footer"><span>Ecossistema jurídico · Aplicações integradas</span><span>As recomendações de IA exigem revisão humana.</span></footer>
      </div>
    </main>
  `,
})
export class EcosystemHomeComponent {}
