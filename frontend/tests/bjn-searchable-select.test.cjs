/** Testes de regressão do seletor pesquisável sem depender do servidor Angular. */
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const ts=require('typescript');
const vm=require('node:vm');
const read=(file)=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
const component=read('src/app/bjn/demands/searchable-select.component.ts');
const registration=read('src/app/bjn/demands/demand-new.component.ts');
const listing=read('src/app/bjn/demands/demand-list.component.ts');

test('normaliza códigos e nomes com acentos para pesquisa no CSV',()=>{
  const sourceFile=ts.createSourceFile('searchable-select.component.ts',component,ts.ScriptTarget.Latest,true,ts.ScriptKind.TS);
  assert.equal(sourceFile.parseDiagnostics.length,0);
  const normalizeNode=sourceFile.statements.find(node=>ts.isFunctionDeclaration(node)&&node.name?.text==='normalizeDirectorySearch');
  assert.ok(normalizeNode,'O componente precisa expor a normalização testável');
  const executable=ts.transpileModule(normalizeNode.getText(sourceFile).replace(/^export\s+/,''),{compilerOptions:{target:ts.ScriptTarget.ES2022}}).outputText;
  const normalize=vm.runInNewContext(`${executable};normalizeDirectorySearch`);
  assert.equal(normalize('4040 - Jurídico'),'4040 - juridico');
  assert.equal(normalize('1234 - São Bento'),'1234 - sao bento');
  assert.ok(normalize('1234 - São Bento').includes(normalize('São')));
  assert.ok(normalize('1234 - São Bento').includes(normalize('1234')));
});

test('lista permite abrir, filtrar e escolher por teclado ou clique',()=>{
  for(const fragment of ['role="combobox"','role="listbox"','role="option"','aria-autocomplete="list"',"event.key==='ArrowDown'","event.key==='ArrowUp'","event.key==='Enter'","event.key==='Escape'",'selectOption(option)','valueChange.emit','document:pointerdown']){
    assert.ok(component.includes(fragment),`Recurso do seletor ausente: ${fragment}`);
  }
  assert.match(component,/maxVisibleOptions=40/);
  assert.match(component,/normalizeDirectorySearch\(option\)\.includes\(term\)/);
  assert.match(component,/!this\.allowCustomValue/);
});

test('cadastro utiliza seleção vinculada ao CSV para os dois departamentos',()=>{
  assert.match(registration,/inputId="consulted-dept"/);
  assert.match(registration,/inputId="dept"/);
  assert.match(registration,/\[options\]="configuration\(\)\?\.department_options \|\| \[\]"/);
  assert.match(registration,/this\.configuration\(\)\?\.department_options\.includes\(this\.form\.requesting_department\)/);
  assert.match(registration,/this\.form\.consulted_department==='4040 - Jurídico'/);
});

test('agência mantém consulta parcial mesmo com catálogo ainda vazio',()=>{
  assert.match(registration,/inputId="agency"/);
  assert.match(listing,/inputId="bjn-agency-options"/);
  assert.match(registration,/\[allowCustomValue\]="true"/);
  assert.match(listing,/\[allowCustomValue\]="true"/);
  assert.match(listing,/branch:this\.branch/);
  assert.match(listing,/\[options\]="configuration\(\)\?\.agency_options \|\| \[\]"/);
});

test('filtro retira a explicação anterior e mantém alinhamento responsivo',()=>{
  const styles=read('src/demand-dashboard.scss');
  const combos=read('src/app/bjn/demands/demands.scss');
  assert.doesNotMatch(listing,/Pesquise por parte do número ou nome/);
  assert.doesNotMatch(listing,/As sugestões vêm do CSV/);
  assert.match(styles,/\.demand-search-primary\{display:grid/);
  assert.match(styles,/\.bjn-filters-extended>\.bjn-filter-field/);
  assert.match(styles,/@media\(max-width:620px\)/);
  assert.match(combos,/\.bjn-combobox-popover/);
});

test('seleção funcional filtra por nome sem acento e preserva busca parcial de agência',()=>{
  // Os decoradores são substituídos apenas neste teste de lógica, sem navegar pelo browser.
  class FakeEmitter {constructor(){this.values=[];} emit(value){this.values.push(value);}}
  const noopDecorator=()=>()=>{};
  const angular={
    Component:()=>target=>target, Input:noopDecorator, Output:noopDecorator,
    ViewChild:noopDecorator, HostListener:noopDecorator,
    EventEmitter:FakeEmitter, ElementRef:class {}, inject:()=>({nativeElement:{contains:()=>false}})
  };
  const js=ts.transpileModule(component,{compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,experimentalDecorators:true}}).outputText;
  const sandbox={exports:{},require:(name)=>name==='@angular/core'?angular:name==='@angular/common'?{CommonModule:class {}}:null};
  vm.runInNewContext(js,sandbox);
  const Select=sandbox.exports.BjnSearchableSelectComponent;
  const dept=new Select();
  dept.inputId='dept';dept.options=['4040 - Jurídico','1222 - São Bento'];
  dept.openMenu();assert.equal(dept.matches.length,2);
  dept.onInput({target:{value:'juridico'}});
  assert.equal(dept.matches.length,1);
  assert.equal(dept.matches[0],'4040 - Jurídico');
  dept.onKeydown({key:'Enter',preventDefault(){}});
  assert.equal(dept.valueChange.values.at(-1),'4040 - Jurídico');
  assert.equal(dept.inputText,'4040 - Jurídico');
  const agency=new Select();
  agency.options=[];agency.allowCustomValue=true;
  agency.onInput({target:{value:'4321'}});
  assert.equal(agency.valueChange.values.at(-1),'4321');
  assert.equal(agency.inputText,'4321');
});
