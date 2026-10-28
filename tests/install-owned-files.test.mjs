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
   let receipt=read();assert.equal(receipt.productVersion,'3.0.0-rc.6');assert.deepEqual(receipt.selected,['orchestrator']);
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
   // Per-file swaps preserve dependencies and runtime data inside managed roots.
   const dependency=path.join(agents,'skills/orchestrator/node_modules/local-user-data.txt');
   fs.mkdirSync(path.dirname(dependency),{recursive:true});fs.writeFileSync(dependency,'preserve generated data');
   const generatedUpgrade=run(['--profile','core']);assert.equal(generatedUpgrade.status,0,generatedUpgrade.stderr);
   assert.equal(fs.readFileSync(dependency,'utf8'),'preserve generated data');
   fs.rmSync(path.dirname(dependency),{recursive:true});
   // Fail after swaps and prove bytes, modes and directory state are restored.
   const beforeFail=snapshot(temp);
   const fail=run(['--profile','domain','--skill','tester'],{CENTURION_INSTALL_TEST_FAIL_AFTER:'3'});
   assert.notEqual(fail.status,0);assert.match(fail.stderr,/Injected install failure/);assert.deepEqual(snapshot(temp),beforeFail);
   // Unrelated client configuration is outside package ownership and unchanged.
   const foreign=path.join(native,'settings.json');fs.writeFileSync(foreign,'{"hooks":{"unknown":true}}\n');
   const foreignBytes=fs.readFileSync(foreign);
   const mixed=run(['--profile','core']);assert.equal(mixed.status,0,mixed.stderr);assert.deepEqual(fs.readFileSync(foreign),foreignBytes);
   const mixedAudit=auditClient(client,targetArgs);assert.equal(mixedAudit.ok,true,JSON.stringify(mixedAudit.failures));
   fs.rmSync(foreign);
   // Tampered owned instruction is also an explicit conflict; its owner bytes are preserved.
   fs.appendFileSync(core,'foreign override\n');const tampered=snapshot(temp);
   assert.notEqual(run(['--profile','core']).status,0);assert.deepEqual(snapshot(temp),tampered);
  }finally{process.env.PATH=savedPath;}
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});

for(const client of clients) test(`${client}: archived Open Design retires owned files and preserves general design skills`,()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-archive-install-'));
 const native=path.join(temp,client),agents=client==='codex'?path.join(temp,'agents'):native;
 const targetArgs=client==='codex'?['--agents-home',agents,'--codex-home',native]:[`--${client}-home`,native];
 const design=['aedilis','pictor','nomenclator','orator','tabularius'];
 const selection=['--profile','domain',...design.flatMap(name=>['--skill',name])];
 const run=args=>spawnSync(process.execPath,[installer,'--client',client,...targetArgs,...args],{cwd:temp,encoding:'utf8'});
 const receiptPath=path.join(native,'centurion/installed-chain.json');
 try {
  const installed=run(selection);assert.equal(installed.status,0,installed.stderr);
  for(const name of design)assert.equal(fs.readFileSync(path.join(agents,'skills',name,'SKILL.md'),'utf8'),fs.readFileSync(path.join(ROOT,'skills',name,'SKILL.md'),'utf8'));
  let receipt=JSON.parse(fs.readFileSync(receiptPath,'utf8'));
  assert(!receipt.files.some(row=>row.sourcePath?.includes('/archive/')||row.installedPath.includes('open-design')));
  const before=snapshot(temp);
  const rejected=run(['--profile','domain','--skill','open-design-producer']);
  assert.notEqual(rejected.status,0);assert.match(rejected.stderr,/allowlist/);assert.deepEqual(snapshot(temp),before);
  // Reconstruct previously owned Open Design rows, not arbitrary home files.
  const archived=path.join(ROOT,'archive/open-design');
  const legacySkill=path.join(agents,'skills',client==='hermes'?'autonomous-ai-agents/open-design-producer':'open-design-producer');
  const priorFiles=walkFiles(path.join(archived,'skills/open-design-producer')).map(source=>({source,target:path.join(legacySkill,path.relative(path.join(archived,'skills/open-design-producer'),source))}));
  const config=path.join(native,'centurion/open-design-bridge.json');
  priorFiles.push({content:'{"configVersion":"CENTURION_OPEN_DESIGN_CONFIG_V1","bridgeRoot":"/historical/source"}\n',target:config});
  if(client==='hermes')priorFiles.push({source:path.join(archived,'integrations/hermes-legion-kit/skill-bundles/aquila-design-production.yaml'),target:path.join(native,'skill-bundles/aquila-design-production.yaml')});
  if(client==='claude')priorFiles.push({source:path.join(archived,'integrations/claude-legion-kit/plugin/scripts/open-design-mcp.mjs'),target:path.join(agents,'skills/centurion-legion/scripts/open-design-mcp.mjs')});
  for(const row of priorFiles){
   fs.mkdirSync(path.dirname(row.target),{recursive:true});fs.writeFileSync(row.target,row.source?fs.readFileSync(row.source):row.content);
   receipt.files.push({installedPath:row.target,installedSha256:hash(fs.readFileSync(row.target)),installedMode:fs.statSync(row.target).mode&0o777});
  }
  receipt.selected.push('open-design-producer');fs.writeFileSync(receiptPath,JSON.stringify(receipt));
  const local=path.join(legacySkill,'node_modules/local-user-data.txt');
  fs.mkdirSync(path.dirname(local),{recursive:true});fs.writeFileSync(local,'keep local data');
  const entry=path.join(legacySkill,'SKILL.md'),original=fs.readFileSync(entry);
  fs.appendFileSync(entry,'local modification\n');const dirty=snapshot(temp);
  const conflict=run(selection);assert.notEqual(conflict.status,0);assert.match(conflict.stderr,/preimage changed/);assert.deepEqual(snapshot(temp),dirty);
  fs.writeFileSync(entry,original);
  const upgraded=run(selection);assert.equal(upgraded.status,0,upgraded.stderr);
  for(const row of priorFiles)assert(!fs.existsSync(row.target),`retired file remains: ${row.target}`);
  assert.equal(fs.readFileSync(local,'utf8'),'keep local data');
  receipt=JSON.parse(fs.readFileSync(receiptPath,'utf8'));
  assert(!receipt.selected.includes('open-design-producer'));
  assert(!receipt.files.some(row=>row.sourcePath?.includes('/archive/')||row.installedPath.includes('open-design')));
  for(const name of design)assert(fs.existsSync(path.join(agents,'skills',name,'SKILL.md')));
  assert.equal(auditClient(client,targetArgs).ok,true);
 }finally{fs.rmSync(temp,{recursive:true,force:true});}
});

for(const client of clients) test(`${client}: explicit legacy preimages preserve custom instructions and runtime state`,()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-legacy-migration-'));
 const native=path.join(temp,client),agents=client==='codex'?path.join(temp,'agents'):native;
 const targetArgs=client==='codex'?['--agents-home',agents,'--codex-home',native]:[`--${client}-home`,native];
 const run=(args=[],env={})=>spawnSync(process.execPath,[installer,'--client',client,...targetArgs,'--profile','core',...args],{encoding:'utf8',env:{...process.env,...env}});
 const instruction=path.join(native,{codex:'AGENTS.md',claude:'CLAUDE.md',hermes:'SOUL.md'}[client]);
 const core=path.join(agents,'skills/orchestrator/SKILL.md');
 const legacyControl=path.join(agents,'skills/orchestrator/scripts/mission_control.py');
 const record=path.join(temp,'migration.json');
 try {
  for(const file of [instruction,core,legacyControl])fs.mkdirSync(path.dirname(file),{recursive:true});
  const original=Buffer.from('# Моя политика\r\nUser policy remains authoritative.\r\n');
  fs.writeFileSync(instruction,original);fs.writeFileSync(core,'legacy orchestrator\n');fs.writeFileSync(legacyControl,'# retired legacy controller\n');
  const state=path.join(agents,'skills/orchestrator/.centurion/runtime.json');
  fs.mkdirSync(path.dirname(state),{recursive:true});fs.writeFileSync(state,'{"keep":"runtime"}\n');
  // These would fail any old whole-home traversal. They are never package files.
  fs.symlinkSync('/not/a/real/credential/path',path.join(native,'auth.json'));
  fs.symlinkSync('/not/a/real/runtime/path',path.join(path.dirname(state),'external-state'));
  const config=path.join(native,'settings.json');fs.writeFileSync(config,'{"hooks":{"user":true},"secret":"fixture-only"}\n');
  const before=snapshot(temp);
  const missing=run();assert.notEqual(missing.status,0);assert.match(missing.stderr,/Foreign managed/);assert.deepEqual(snapshot(temp),before);
  const migration={migrationVersion:'CENTURION_INSTALL_MIGRATION_V1',client,files:[
   {installedPath:instruction,installedSha256:hash(original),action:'preserve-instruction'},
   {installedPath:core,installedSha256:hash(fs.readFileSync(core)),action:'replace'},
   {installedPath:legacyControl,installedSha256:hash(fs.readFileSync(legacyControl)),action:'retire'}
  ]};
  fs.writeFileSync(record,JSON.stringify({...migration,files:[...migration.files,{installedPath:config,installedSha256:hash(fs.readFileSync(config)),action:'retire'}]}));
  const invalidBefore=snapshot(temp);const invalid=run(['--migration-record',record]);assert.notEqual(invalid.status,0);assert.match(invalid.stderr,/Invalid managed manifest/);assert.deepEqual(snapshot(temp),invalidBefore);
  const validHash=migration.files[1].installedSha256;migration.files[1].installedSha256='0'.repeat(64);
  fs.writeFileSync(record,JSON.stringify(migration));const staleBefore=snapshot(temp);const stale=run(['--migration-record',record]);assert.notEqual(stale.status,0);assert.match(stale.stderr,/preimage changed/);assert.deepEqual(snapshot(temp),staleBefore);
  migration.files[1].installedSha256=validHash;
  fs.writeFileSync(record,JSON.stringify(migration));
  const beforeDry=snapshot(temp);
  const dry=run(['--migration-record',record,'--dry-run']);assert.equal(dry.status,0,dry.stderr);assert.deepEqual(snapshot(temp),beforeDry);
  const planned=JSON.parse(dry.stdout);assert(planned.targets.includes(path.join(native,'centurion/installed-chain.json')));
  if(client==='claude')assert(planned.targets.includes(path.join(native,'skills/centurion-legion/.mcp.json')));
  assert.deepEqual(planned.retired,[legacyControl]);assert.equal(planned.preservedInstruction,true);
  const failed=run(['--migration-record',record],{CENTURION_INSTALL_TEST_FAIL_AFTER:'2'});
  assert.notEqual(failed.status,0);assert.match(failed.stderr,/Injected install failure/);assert.deepEqual(snapshot(temp),beforeDry);
  const success=run(['--migration-record',record]);assert.equal(success.status,0,success.stderr);
  const content=fs.readFileSync(instruction);assert.deepEqual(content.subarray(0,original.length),original);
  assert.equal(content.toString('utf8').split('<!-- CENTURION_MANAGED_V3_START -->').length,2);
  assert(!fs.existsSync(legacyControl));assert.equal(fs.readFileSync(state,'utf8'),'{"keep":"runtime"}\n');
  assert.equal(fs.readlinkSync(path.join(native,'auth.json')),'/not/a/real/credential/path');
  assert.equal(fs.readFileSync(config,'utf8'),'{"hooks":{"user":true},"secret":"fixture-only"}\n');
  const audit=auditClient(client,targetArgs);assert.equal(audit.ok,true,JSON.stringify(audit.failures));
  assert.equal(audit.auditScope,'explicit-package-files');assert.equal(audit.liveLoadedChainProven,false);
  const upgrade=run();assert.equal(upgrade.status,0,upgrade.stderr);assert.deepEqual(fs.readFileSync(instruction),content);
  fs.appendFileSync(instruction,'\nNew user suffix\n');const userChanged=snapshot(temp);
  const instructionConflict=run();assert.notEqual(instructionConflict.status,0);assert.match(instructionConflict.stderr,/preimage changed/);assert.deepEqual(snapshot(temp),userChanged);
  fs.writeFileSync(instruction,content);
  const replay=run(['--migration-record',record]);assert.notEqual(replay.status,0);assert.match(replay.stderr,/legacy home/);
  // Unknown/new package instruction leaves remain explicit metadata conflicts.
  const extra=path.join(agents,'skills/coder/SKILL.md');fs.mkdirSync(path.dirname(extra),{recursive:true});fs.writeFileSync(extra,'foreign recipe\n');
  const extraBefore=snapshot(temp);const conflict=run();assert.notEqual(conflict.status,0);assert.match(conflict.stderr,/Foreign managed instruction/);assert.deepEqual(snapshot(temp),extraBefore);
  assert.equal(auditClient(client,targetArgs).ok,false);fs.rmSync(extra);
  // Forged receipt paths cannot turn unrelated configuration into owned data.
  const installedManifest=path.join(native,'centurion/installed-chain.json');
  const receipt=JSON.parse(fs.readFileSync(installedManifest,'utf8'));
  receipt.files.push({installedPath:config,installedSha256:hash(fs.readFileSync(config))});fs.writeFileSync(installedManifest,JSON.stringify(receipt));
  const forgedBefore=snapshot(temp);const forged=run();assert.notEqual(forged.status,0);assert.match(forged.stderr,/Invalid managed manifest/);assert.deepEqual(snapshot(temp),forgedBefore);
  assert.throws(()=>auditClient(client,targetArgs),/Invalid managed manifest/);
 } finally {fs.rmSync(temp,{recursive:true,force:true});}
});

test('preserved instruction ranges cannot hide an empty or malformed managed wrapper',()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),'centurion-preserved-ranges-'));
 const native=path.join(temp,'codex'),agents=path.join(temp,'agents');
 const args=['--agents-home',agents,'--codex-home',native];
 const run=(extra=[])=>spawnSync(process.execPath,[installer,'--client','codex',...args,'--profile','core',...extra],{encoding:'utf8'});
 const instruction=path.join(native,'AGENTS.md'),manifest=path.join(native,'centurion/installed-chain.json');
 try {
  fs.mkdirSync(native,{recursive:true});
  const prefix=Buffer.from('# Custom user instructions\r\nPreserve these exact bytes.\r\n');
  fs.writeFileSync(instruction,prefix);
  const record=path.join(temp,'migration.json');
  fs.writeFileSync(record,JSON.stringify({migrationVersion:'CENTURION_INSTALL_MIGRATION_V1',client:'codex',files:[{installedPath:instruction,installedSha256:hash(prefix),action:'preserve-instruction'}]}));
  const installed=run(['--migration-record',record]);assert.equal(installed.status,0,installed.stderr);
  const originalBytes=fs.readFileSync(instruction),originalReceipt=fs.readFileSync(manifest);
  assert.equal(auditClient('codex',args).ok,true);
  const start='\n\n<!-- CENTURION_MANAGED_V3_START -->\n',end='\n<!-- CENTURION_MANAGED_V3_END -->\n';
  const cases=[
   {name:'all bytes claimed as preserved prefix',bytes:originalBytes,prefixBytes:originalBytes.length,suffixBytes:0},
   {name:'opening delimiter hidden in prefix',bytes:originalBytes,prefixBytes:prefix.length+Buffer.byteLength(start),suffixBytes:0},
   {name:'empty wrapper',bytes:Buffer.concat([prefix,Buffer.from(start+' \n'+end)]),prefixBytes:prefix.length,suffixBytes:0},
   {name:'wrong closing delimiter',bytes:Buffer.concat([prefix,Buffer.from(start+'# wrapper\n'+end.replace('_END','_BROKEN'))]),prefixBytes:prefix.length,suffixBytes:0}
  ];
  for(const fixture of cases) {
   const receipt=JSON.parse(originalReceipt),row=receipt.files.find(r=>r.installedPath===instruction);
   row.renderedContent=fixture.bytes.toString('utf8');row.installedSha256=row.sourceSha256=hash(fixture.bytes);
   row.preservedInstruction={prefixBytes:fixture.prefixBytes,suffixBytes:fixture.suffixBytes,prefixSha256:hash(fixture.bytes.subarray(0,fixture.prefixBytes)),suffixSha256:hash(fixture.bytes.subarray(fixture.bytes.length-fixture.suffixBytes))};
   fs.writeFileSync(instruction,fixture.bytes);fs.writeFileSync(manifest,JSON.stringify(receipt));
   const audit=auditClient('codex',args),before=snapshot(temp),upgrade=run();
   assert.equal(audit.ok,false,fixture.name+' bypassed audit; upgrade exit='+upgrade.status);
   assert(audit.failures.some(f=>/preserved instruction/i.test(f.reason)),JSON.stringify(audit.failures));
   assert.notEqual(upgrade.status,0,fixture.name+' bypassed upgrade');
   assert.match(upgrade.stderr,/preserved instruction/i);assert.deepEqual(snapshot(temp),before);
  }
  fs.writeFileSync(instruction,originalBytes);fs.writeFileSync(manifest,originalReceipt);
  const validUpgrade=run();assert.equal(validUpgrade.status,0,validUpgrade.stderr);
  assert.deepEqual(fs.readFileSync(instruction),originalBytes);assert.deepEqual(originalBytes.subarray(0,prefix.length),prefix);
  assert.equal(auditClient('codex',args).ok,true);
 } finally {fs.rmSync(temp,{recursive:true,force:true});}
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
