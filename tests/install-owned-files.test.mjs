import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { LOAD_MAP,walkFiles,selectSkills } from '../integrations/codex-legion-kit/scripts/lib/surface-config.mjs';
import { auditClient } from '../integrations/codex-legion-kit/scripts/codex-surface-audit.mjs';
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const installer=path.join(ROOT,'scripts/install-owned-files.mjs');
const hash=b=>createHash('sha256').update(b).digest('hex');
const clients=process.env.CENTURION_INSTALL_CLIENT?[process.env.CENTURION_INSTALL_CLIENT]:['codex','claude','hermes'];
function snapshot(root){
 const records=[];
 function visit(dir){for(const name of fs.readdirSync(dir).sort()){
  const p=path.join(dir,name),s=fs.lstatSync(p);
  records.push([path.relative(root,p),s.mode&0o777,s.isSymbolicLink()?'symlink':s.isDirectory()?'directory':hash(fs.readFileSync(p))]);
  if(s.isDirectory())visit(p);
 }}visit(root);return records;
}
for(const client of clients) test(`${client}: selected cold/upgrade install, chain readback, conflicts and transactional rollback`,()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-owned-install-'));
 const native=path.join(temp,client),agents=client==='codex'?path.join(temp,'agents'):native;
 const targetArgs=client==='codex'?['--agents-home',agents,'--codex-home',native]:[`--${client}-home`,native];
 const run=(args,env={})=>spawnSync(process.execPath,[installer,'--client',client,...targetArgs,...args],{
  cwd:temp,encoding:'utf8',env:{...process.env,...env}});
 const receiptPath=path.join(native,'centurion/installed-chain.json');
 const read=()=>JSON.parse(fs.readFileSync(receiptPath,'utf8'));
 try {
  // Make any accidental client startup/update a hard fixture failure.
  const bin=path.join(temp,'bin');fs.mkdirSync(bin);
  for(const command of ['hermes','claude','codex'])fs.writeFileSync(path.join(bin,command),'#!/bin/sh\necho accidental live client startup >&2\nexit 91\n',{mode:0o755});
  const savedPath=process.env.PATH;process.env.PATH=bin+path.delimiter+savedPath;
  try {
   const before=snapshot(temp);
   const dry=run(['--profile','core','--dry-run']);assert.equal(dry.status,0,dry.stderr);assert.deepEqual(snapshot(temp),before);
   assert.notEqual(run([]).status,0,'implicit selection accepted');
   const cold=run(['--profile','core']);assert.equal(cold.status,0,cold.stderr);
   let receipt=read();assert.equal(receipt.productVersion,'3.0.0-rc.1');assert.deepEqual(receipt.selected,['orchestrator']);
   assert.equal(receipt.capability.status,'excluded');assert.equal(receipt.liveLoadedChainProven,false);
   for(const file of receipt.files){
    assert.equal(hash(fs.readFileSync(file.installedPath)),file.installedSha256);
    assert.equal(file.sourceSha256,file.installedSha256);
    if(file.generated)assert.equal(hash(file.renderedContent),file.sourceSha256);else assert.equal(hash(fs.readFileSync(file.sourcePath)),file.sourceSha256);
   }
   assert(!walkFiles(agents).some(p=>/mission_control|evocate\.sh|deep-search|browse\.js|\/research-paper-writing\//.test(p)));
   if(client==='claude')assert.deepEqual(JSON.parse(fs.readFileSync(path.join(native,'skills/centurion-legion/.mcp.json'),'utf8')),{mcpServers:{}});
   if(client==='hermes'){
    assert(fs.existsSync(path.join(native,'SOUL.md')));
    assert(!fs.existsSync(path.join(native,'config.yaml')));
    const bundle=fs.readFileSync(path.join(native,'skill-bundles/aquila-delivery.yaml'),'utf8');
    assert(!/delegate_task|agy|kanban|delegated-cli|delegating-code/.test(bundle));
   }
   // Upgrade a previously owned stale override. Record prior bytes as the old release receipt.
   const core=path.join(agents,'skills/orchestrator/SKILL.md');
   fs.writeFileSync(core,'old owned instruction: three retries and legacy route\n');
   receipt.files.find(r=>r.installedPath===core).installedSha256=hash(fs.readFileSync(core));
   fs.writeFileSync(receiptPath,JSON.stringify(receipt));
   const upgraded=run(['--profile','domain','--skill','coder','--skill','researcher']);assert.equal(upgraded.status,0,upgraded.stderr);
   assert.equal(fs.readFileSync(core,'utf8'),fs.readFileSync(path.join(ROOT,'skills/orchestrator/SKILL.md'),'utf8'));
   assert(!walkFiles(agents).some(p=>/\/researcher\/(?:scripts\/|package(?:-lock)?\.json)/.test(p)));
   const audit=auditClient(client,[...targetArgs,'--json']);assert.equal(audit.ok,true,JSON.stringify(audit.failures));
   // Switching back removes previous selected entrypoints and plugin projections, without old override fallback.
   const switched=run(['--profile','core']);assert.equal(switched.status,0,switched.stderr);
   assert(!fs.existsSync(path.join(agents,'skills/coder/SKILL.md')));
   assert(!fs.existsSync(path.join(native,'skills/centurion-legion/agents/coder.md')));
   assert.deepEqual(read().selected,selectSkills('core'));
   if(client==='hermes') {
    const maintenance=run(['--profile','maintenance','--skill','aquila-executor-eval']);
    assert.equal(maintenance.status,0,maintenance.stderr);
    assert(fs.existsSync(path.join(native,'skill-bundles/aquila-executor-eval.yaml')));
    assert(!fs.existsSync(path.join(native,'skills/autonomous-ai-agents/aquila-self-debug/SKILL.md')));
    const domain=run(['--profile','domain','--skill','solana-program-engineering']);
    assert.equal(domain.status,0,domain.stderr);
    assert(fs.existsSync(path.join(native,'skills/software-development/solana-program-engineering/SKILL.md')));
    assert(!fs.existsSync(path.join(native,'skill-bundles/aquila-executor-eval.yaml')));
    assert.equal(run(['--profile','core']).status,0);
   }
   // Ignored dependencies are outside the audit but must never be silently discarded by a swap.
   const dependency=path.join(agents,'skills/orchestrator/node_modules/local-user-data.txt');
   fs.mkdirSync(path.dirname(dependency),{recursive:true});fs.writeFileSync(dependency,'preserve generated data');
   const generatedBefore=snapshot(temp);
   const generatedConflict=run(['--profile','core']);assert.notEqual(generatedConflict.status,0);
   assert.match(generatedConflict.stderr,/Foreign\/generated surface conflict/);assert.deepEqual(snapshot(temp),generatedBefore);
   fs.rmSync(path.dirname(dependency),{recursive:true});
   // Fail after swaps and prove bytes, modes and directory state are restored.
   const beforeFail=snapshot(temp);
   const fail=run(['--profile','domain','--skill','tester'],{CENTURION_INSTALL_TEST_FAIL_AFTER:'3'});
   assert.notEqual(fail.status,0);assert.match(fail.stderr,/Injected install failure/);assert.deepEqual(snapshot(temp),beforeFail);
   // A foreign global instruction is a conflict, never an automatic rewrite.
   const foreign=path.join(native,'settings.json');fs.writeFileSync(foreign,'{"hooks":{"unknown":true}}\n');
   const withForeign=snapshot(temp);
   const conflict=run(['--profile','core']);assert.notEqual(conflict.status,0);assert.match(conflict.stderr,/Foreign\/global surface conflict/);assert.deepEqual(snapshot(temp),withForeign);
   const conflictingAudit=auditClient(client,targetArgs);assert.equal(conflictingAudit.ok,false);
   fs.rmSync(foreign);
   // Tampered owned instruction is also an explicit conflict; its owner bytes are preserved.
   fs.appendFileSync(core,'foreign override\n');const tampered=snapshot(temp);
   assert.notEqual(run(['--profile','core']).status,0);assert.deepEqual(snapshot(temp),tampered);
  }finally{process.env.PATH=savedPath;}
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});

test('selection rejects excluded and incorporated identities; symlink ancestors never receive writes',()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-owned-conflict-'));
 try{
  for(const n of [...LOAD_MAP.excluded,...LOAD_MAP.incorporated])assert.throws(()=>selectSkills('domain',[n]));
  const outside=path.join(temp,'outside');fs.mkdirSync(outside);fs.symlinkSync(outside,path.join(temp,'agents'));
  const r=spawnSync(process.execPath,[installer,'--client','codex','--profile','core','--agents-home',path.join(temp,'agents'),'--codex-home',path.join(temp,'codex')],{encoding:'utf8'});
  assert.notEqual(r.status,0);assert.match(r.stderr,/Symlink/);assert.deepEqual(fs.readdirSync(outside),[]);
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});

test('installed support library preserves real TLS certificate verification',()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-owned-tls-'));
 try {
  const agents=path.join(temp,'agents'),native=path.join(temp,'codex');
  const install=spawnSync(process.execPath,[installer,'--client','codex','--profile','domain','--skill','velites',
   '--agents-home',agents,'--codex-home',native],{encoding:'utf8'});
  assert.equal(install.status,0,install.stderr);
  const library=path.join(agents,'libs/legion_core.py');
  assert.equal(hash(fs.readFileSync(library)),hash(fs.readFileSync(path.join(ROOT,'libs/legion_core.py'))));
  const key=path.join(temp,'key.pem'),cert=path.join(temp,'cert.pem');
  const openssl=spawnSync('openssl',['req','-x509','-newkey','rsa:2048','-nodes','-keyout',key,'-out',cert,
   '-days','1','-subj','/CN=localhost'],{encoding:'utf8'});
  assert.equal(openssl.status,0,openssl.stderr);
  // Memory BIO performs a real TLS handshake without a sandbox-dependent listener.
  const python=spawnSync('python3',['-c',`
import importlib.util, ssl, sys
before = ssl._create_default_https_context
spec = importlib.util.spec_from_file_location('installed_legion_core', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert ssl._create_default_https_context is before is ssl.create_default_context
server_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
server_context.load_cert_chain(sys.argv[2], sys.argv[3])
client_in, client_out, server_in, server_out = (ssl.MemoryBIO() for _ in range(4))
client = ssl._create_default_https_context().wrap_bio(client_in, client_out, server_hostname='localhost')
server = server_context.wrap_bio(server_in, server_out, server_side=True)
for _ in range(10):
    try:
        client.do_handshake()
    except ssl.SSLCertVerificationError:
        print('untrusted TLS certificate rejected')
        break
    except ssl.SSLWantReadError:
        pass
    if client_out.pending:
        server_in.write(client_out.read())
    try:
        server.do_handshake()
    except ssl.SSLWantReadError:
        pass
    if server_out.pending:
        client_in.write(server_out.read())
else:
    raise AssertionError('untrusted TLS certificate was accepted or handshake did not verify')
`,library,cert,key],{encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'}});
  assert.equal(python.status,0,python.stderr);
  assert.match(python.stdout,/untrusted TLS certificate rejected/);
 } finally {fs.rmSync(temp,{recursive:true,force:true});}
});

test('capability receipts bind binary/config/route/adapter and invalidate without a probe',()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-capability-'));
 try {
  const files={binaryPath:'mock-binary',configPath:'mock-config',routePath:'mock-route',evidencePath:'mock-help'};
  for(const [key,name] of Object.entries(files)) {
   files[key]=path.join(temp,name);fs.writeFileSync(files[key],'offline fixture '+name);
  }
  const adapter=path.join(ROOT,'integrations/hermes-legion-kit/skills/autonomous-ai-agents/agent-contract-runner/scripts/result_gateway.py');
  const receipt={client:'codex',adapterVersion:'centurion-native-v3',binaryVersion:'fixture-1',
   supportedFlags:['--output-last-message','--output-schema'],nativeSchemaSupported:true,
   permissionMode:'read-only-fixture',extractionMode:'file-candidate',...files,
   binarySha256:hash(fs.readFileSync(files.binaryPath)),configSha256:hash(fs.readFileSync(files.configPath)),
   routeSha256:hash(fs.readFileSync(files.routePath)),evidenceSha256:hash(fs.readFileSync(files.evidencePath)),
   adapterSha256:hash(fs.readFileSync(adapter))};
  const record=path.join(temp,'receipt.json');fs.writeFileSync(record,JSON.stringify(receipt));
  const run=()=>spawnSync(process.execPath,[installer,'--client','codex','--profile','core','--dry-run',
   '--agents-home',path.join(temp,'agents'),'--codex-home',path.join(temp,'codex'),'--capability-record',record],{encoding:'utf8'});
  const valid=run();assert.equal(valid.status,0,valid.stderr);assert.equal(JSON.parse(valid.stdout).adapter.status,'recorded');
  assert.equal(JSON.parse(valid.stdout).adapter.liveDispatchProven,false);
  fs.appendFileSync(files.routePath,' route changed');
  const changed=run();assert.equal(changed.status,0,changed.stderr);assert.equal(JSON.parse(changed.stdout).adapter.status,'excluded');
  assert(!fs.existsSync(path.join(temp,'codex')),'dry-run wrote native home');
 } finally {fs.rmSync(temp,{recursive:true,force:true});}
});
