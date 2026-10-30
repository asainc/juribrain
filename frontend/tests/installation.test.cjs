/**
 * Testes de regressão do instalador para evitar o erro npm edgesOut e
 * impedir que o frontend inicie com o builder Angular incompleto.
 * Nenhum teste acessa a rede ou usa arquivos de produção.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const importCore = () => import('../scripts/install-core.mjs');
const importDoctor = () => import('../scripts/doctor.mjs');

test('identifica somente a falha específica edgesOut do npm', async () => {
  const { isPeerGraphCrash } = await importCore();
  assert.equal(isPeerGraphCrash("npm error Cannot read properties of null (reading 'edgesOut')"), true);
  assert.equal(isPeerGraphCrash('npm ERR! ERESOLVE unable to resolve dependency tree'), false);
  assert.equal(isPeerGraphCrash('npm ERR! E401 Unauthorized'), false);
  assert.equal(isPeerGraphCrash('npm ERR! getaddrinfo ENOTFOUND'), false);
});

test('instalação padrão não altera política de peers sem o erro', async () => {
  const { installArguments } = await importCore();
  const args = installArguments({hasLockFile:false});
  assert.equal(args[0], 'install');
  assert.ok(args.includes('--include=dev'));
  assert.ok(args.includes('--include=optional'));
  assert.ok(!args.includes('--legacy-peer-deps'));
  assert.equal(installArguments({hasLockFile:true})[0], 'ci');
});

test('fallback de peer deps é restrito à repetição corretiva', async () => {
  const { installArguments } = await importCore();
  const args = installArguments({hasLockFile:true,peerWorkaround:true});
  assert.ok(args.includes('--legacy-peer-deps'));
  assert.equal(args[0], 'ci');
});

test('versões aceitas seguem as linhas LTS autorizadas', async () => {
  const { isSupportedNode } = await importCore();
  for (const version of ['22.12.0', '22.16.0', '22.22.0', '24.0.0', '24.10.0']) {
    assert.ok(isSupportedNode(version), version);
  }
  for (const version of ['22.11.0', '20.20.0', '23.0.0', '25.0.0', 'abc']) {
    assert.equal(isSupportedNode(version), false, version);
  }
});

test('doctor acusa o builder ausente ou versão incorreta', async () => {
  const { inspectInstallation } = await importDoctor();
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'legal-angular-check-'));
  try {
    const manifest = {
      dependencies: {'@angular/core':'21.2.19', '@angular/common':'21.2.19'},
      devDependencies: {
        '@angular/cli':'21.2.19', '@angular/build':'21.2.19',
        '@angular/compiler-cli':'21.2.19','typescript':'5.9.3',
      },
    };
    const modules = { '@angular/cli':'21.2.19', '@angular/compiler-cli':'21.2.19', '@angular/core':'21.2.19', '@angular/common':'21.2.19', 'typescript':'5.9.3' };
    for (const [name, version] of Object.entries(modules)) {
      const folder = path.join(temporary, 'node_modules', ...name.split('/'));
      fs.mkdirSync(folder,{recursive:true});
      fs.writeFileSync(path.join(folder,'package.json'), JSON.stringify({version}));
    }
    assert.ok(inspectInstallation(temporary,manifest).some(message => message.includes('@angular/build: não instalado')));
    const buildFolder = path.join(temporary,'node_modules','@angular','build');
    fs.mkdirSync(buildFolder, {recursive:true});
    fs.writeFileSync(path.join(buildFolder,'package.json'), JSON.stringify({version:'20.0.0'}));
    assert.ok(inspectInstallation(temporary,manifest).some(message => message.includes('esperado 21.2.19, encontrado 20.0.0')));
    fs.writeFileSync(path.join(buildFolder,'package.json'), JSON.stringify({version:'21.2.19'}));
    assert.deepEqual(inspectInstallation(temporary,manifest),[]);
  } finally {
    fs.rmSync(temporary, {force:true,recursive:true});
  }
});

test('setup detecta edgesOut e repete apenas com fallback, sem usar rede', async () => {
  const {spawnSync} = require('node:child_process');
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'legal-angular-setup-'));
  try {
    const scriptFolder = path.join(temporary, 'scripts');
    fs.mkdirSync(scriptFolder, {recursive:true});
    for (const fileName of ['setup.mjs','install-core.mjs','doctor.mjs']) {
      fs.copyFileSync(path.join(__dirname,'..','scripts',fileName),path.join(scriptFolder,fileName));
    }
    const rootManifest = require('../package.json');
    fs.writeFileSync(path.join(temporary,'package.json'),JSON.stringify(rootManifest));
    const fakeNpm = path.join(temporary,'fake-npm.js');
    const marker = path.join(temporary,'attempts.txt');
    // Este executável sintético simula o npm e cria apenas metadados temporários.
    const fakeCode = [
      "const fs=require('node:fs');",
      "const path=require('node:path');",
      "const args=process.argv.slice(2);",
      "fs.appendFileSync(process.env.FAKE_MARKER,JSON.stringify(args)+'\\n');",
      "if(!args.includes('--legacy-peer-deps')){console.error(\"Cannot read properties of null (reading 'edgesOut')\");process.exit(1);}",
      "const manifest=JSON.parse(fs.readFileSync(path.join(process.env.FAKE_ROOT,'package.json'),'utf8'));",
      "for(const name of ['@angular/cli','@angular/build','@angular/compiler-cli','@angular/core','@angular/common','typescript']){",
      "const version=manifest.dependencies?.[name]??manifest.devDependencies?.[name];",
      "const dir=path.join(process.env.FAKE_ROOT,'node_modules',...name.split('/'));",
      "fs.mkdirSync(dir,{recursive:true});fs.writeFileSync(path.join(dir,'package.json'),JSON.stringify({version}));}",
    ].join('\n');
    fs.writeFileSync(fakeNpm,fakeCode);
    const result = spawnSync(process.execPath,[path.join(scriptFolder,'setup.mjs')],{
      encoding:'utf8',
      env:{...process.env,npm_execpath:fakeNpm,FAKE_ROOT:temporary,FAKE_MARKER:marker},
      timeout:15_000,
    });
    assert.equal(result.status,0, result.stderr);
    const attempts = fs.readFileSync(marker,'utf8').trim().split('\n').map(JSON.parse);
    assert.equal(attempts.length,2);
    assert.ok(!attempts[0].includes('--legacy-peer-deps'));
    assert.ok(attempts[1].includes('--legacy-peer-deps'));
    assert.match(result.stdout,/Dependências Angular principais encontradas/);
  } finally {
    fs.rmSync(temporary,{recursive:true,force:true});
  }
});
