/** Registro central do menu, catálogo inicial e caminhos de cada aplicação. */
export interface ApplicationDescriptor {
  key: string;
  label: string;
  subtitle: string;
  route: string;
  badge: string;
  category: string;
  description: string;
  routePrefixes: readonly string[];
}

/** Uma nova aplicação normalmente exige apenas este cadastro e sua rota lazy. */
export const APPLICATIONS: readonly ApplicationDescriptor[] = [
  {key:'home',label:'Página inicial',subtitle:'Visão geral das soluções',route:'/',badge:'IN',category:'PORTAL',description:'',routePrefixes:[]},
  {key:'bjn',label:'BJN',subtitle:'Minutas e demandas',route:'/bjn',badge:'BJ',category:'GESTÃO JURÍDICA',description:'Crie minutas a partir do catálogo de cláusulas e gerencie demandas, análises e pareceres jurídicos.',routePrefixes:['/bjn']},
  {key:'auditoria',label:'Auditoria de Pagamentos',subtitle:'Cálculos e conferências',route:'/auditoria-pagamentos/calculo',badge:'AP',category:'CONFERÊNCIA FINANCEIRA',description:'Consulte documentos, execute cálculos judiciais e acompanhe histórico, lotes, índices e qualidade da IA.',routePrefixes:['/auditoria-pagamentos']},
  {key:'chatbot',label:'Chatbot / AI Ready',subtitle:'Inteligência processual',route:'/chatbot',badge:'IA',category:'INTELIGÊNCIA ARTIFICIAL',description:'Explore processos cíveis e trabalhistas com agenda documental, provas, busca nos PDFs e respostas com fontes.',routePrefixes:['/chatbot','/ai-ready']},
  {key:'behavior',label:'Behavior',subtitle:'Simulação multiagente',route:'/behavior',badge:'BE',category:'SIMULAÇÃO E EXPERIMENTAÇÃO',description:'Crie agentes e cenários sintéticos, teste eventos e visualize interações, conversas e resultados de simulações.',routePrefixes:['/behavior','/laboratorio-comportamental']},
];

/** A fronteira da rota impede tratar /bjn-foo como uma rota do BJN. */
export function applicationForUrl(url: string): ApplicationDescriptor {
  const current = url.split(/[?#]/,1)[0];
  return APPLICATIONS.find(app => app.routePrefixes.some(prefix => current === prefix || current.startsWith(`${prefix}/`))) || APPLICATIONS[0];
}
