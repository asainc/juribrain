/** Verifica fluxos estruturais sem depender do Angular instalado no ambiente offline. */
const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=(file)=>fs.readFileSync(path.join(root,file),'utf8');

test('SCSS BJN carregado uma única vez em pacote global sem elevar budget',()=>{
  const config=JSON.parse(read('angular.json'));
  const build=config.projects['ai-ready-legal'].architect.build;
  assert.ok(build.options.styles.includes('src/app/bjn/demands/demands.scss'));
  assert.equal(build.configurations.production.budgets.find(entry=>entry.type==='anyComponentStyle').maximumError,'16kB');
  for(const file of ['demand-new.component.ts','demand-list.component.ts','demand-detail.component.ts']){
    assert.doesNotMatch(read('src/app/bjn/demands/'+file),/styleUrl\s*:\s*['"]\.\/demands\.scss/);
  }
});
test('gestão BJN oferece aba pendente, seleção em lote e filtros de data e advogado',()=>{
  const source=read('src/app/bjn/demands/demand-list.component.ts');
  for(const text of ['Demandas pendentes','tab()','toggleAll','assignSelected','this.api.assignBulk',
                     'from_date:this.fromDate','to_date:this.toDate','lawyer:this.lawyer','pending_only:']){
    assert.ok(source.includes(text),text);
  }
  assert.match(source,/actor\.role!=='admin'/);
});
test('cadastro identifica natureza em PDF e mostra correção antes de enviar',()=>{
  const view=read('src/app/bjn/demands/demand-new.component.ts');
  for(const text of ['verifyNature','this.api.classifyNature','natureClassification','Natureza corrigida automaticamente',
                     'this.form.service_nature=response.detected_nature','classificationGeneration']){
    assert.ok(view.includes(text),text);
  }
  assert.match(view,/\[disabled\]="sending\(\) \|\| classifyingNature\(\)"/);
});
test('API client tem endpoints protegidos de lote e classificação',()=>{
  const client=read('src/app/core/bjn-demand-api.service.ts');
  assert.match(client,/atribuicao\/lote/);
  assert.match(client,/assistente\/classificar-natureza/);
  assert.match(client,/FormData/);
});
