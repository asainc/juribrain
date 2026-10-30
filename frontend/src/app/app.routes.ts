/** Rotas do ecossistema: as telas existentes permanecem independentes e carregadas sob demanda. */
import { Routes } from '@angular/router';
export const routes: Routes = [
  {path: '', pathMatch: 'full', loadComponent: () => import('./home/ecosystem-home.component').then(m => m.EcosystemHomeComponent)},
  {path: 'bjn/demandas/nova', loadComponent: () => import('./bjn/demands/demand-new.component').then(m => m.BjnDemandNewComponent)},
  {path: 'bjn/demandas/:id', loadComponent: () => import('./bjn/demands/demand-detail.component').then(m => m.BjnDemandDetailComponent)},
  {path: 'bjn/demandas', loadComponent: () => import('./bjn/demands/demand-list.component').then(m => m.BjnDemandListComponent)},
  {path: 'bjn', loadComponent: () => import('./bjn/bjn-page.component').then(m => m.BjnPageComponent)},
  {path: 'chatbot', loadComponent: () => import('./chatbot/chatbot-page.component').then(m => m.ChatbotPageComponent)},
  {path: 'ai-ready', redirectTo: 'chatbot', pathMatch: 'full'},
  {path: 'auditoria-pagamentos', children: [
    {path: 'calculo', loadComponent: () => import('./auditoria/calculation/calculation-page.component').then(m => m.CalculationPageComponent)},
    {path: 'historico', loadComponent: () => import('./auditoria/history/calculation-history-page.component').then(m => m.CalculationHistoryPageComponent)},
    {path: 'qualidade-ia', loadComponent: () => import('./auditoria/quality/quality-page.component').then(m => m.QualityPageComponent)},
    {path: 'lotes', loadComponent: () => import('./auditoria/batches/batch-page.component').then(m => m.BatchPageComponent)},
    {path: 'indices', loadComponent: () => import('./auditoria/indices/indices-page.component').then(m => m.IndicesPageComponent)},
    {path: '', pathMatch: 'full', redirectTo: 'calculo'},
  ]},
  {path: '**', redirectTo: ''},
];
