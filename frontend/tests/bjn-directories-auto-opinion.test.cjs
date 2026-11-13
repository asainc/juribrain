/** Testes estruturais dos novos fluxos, independentes da instalação Angular. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const read=(name)=>fs.readFileSync(path.resolve(__dirname,'..',name),'utf8');

test('a jornada começa pelo catálogo de departamentos e só avança com Jurídico',()=>{
  const source=read('src/app/bjn/demands/demand-new.component.ts');
  assert.match(source,/departmentSelected=signal\(false\)/);
  assert.match(source,/consulted-dept/);
  assert.match(source,/configuration\(\)\?\.department_options/);
  assert.match(source,/this\.form\.consulted_department==='4040 - Jurídico'/);
  assert.match(source,/@else if\(!triageComplete\(\)\)/);
  assert.match(source,/\<label for="dept"\>Solicitante/);
  assert.doesNotMatch(source,/\<label for="dept"\>Departamento Solicitante/);
});

test('parecer é solicitado automaticamente e sempre exige revisão humana',()=>{
  const source=read('src/app/bjn/demands/demand-detail.component.ts');
  assert.match(source,/this\.automaticDraftAttempted=true/);
  assert.match(source,/void this\.generateDraft\(\)/);
  assert.doesNotMatch(source,/Preparar rascunho com text_generator/);
  assert.match(source,/humanReviewed/);
  assert.match(source,/this\.api\.publishOpinionWithAttachments/);
});

test('agência é pesquisável por texto parcial e sugerida a partir do catálogo',()=>{
  const source=read('src/app/bjn/demands/demand-list.component.ts');
  const config=read('src/app/core/bjn-demand-api.service.ts');
  assert.match(source,/inputId="bjn-agency-options"/);
  assert.match(source,/configuration\(\)\?\.agency_options/);
  assert.match(source,/\[allowCustomValue\]="true"/);
  assert.match(config,/agency_options:string\[\]/);
  assert.match(config,/consulted_department:string/);
});


test('componentes modificados têm sintaxe TypeScript válida',()=>{
  const ts=require('typescript');
  for(const name of ['src/app/bjn/demands/demand-new.component.ts','src/app/bjn/demands/demand-detail.component.ts','src/app/core/bjn-demand-api.service.ts']){
    const parsed=ts.createSourceFile(name,read(name),ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
    assert.equal(parsed.parseDiagnostics.length,0,`${name}: ${parsed.parseDiagnostics.map(issue=>issue.messageText).join('; ')}`);
  }
});
