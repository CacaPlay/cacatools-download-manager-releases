import {spawn} from 'node:child_process';
import fs from 'node:fs';
import crypto from 'node:crypto';

const exe=process.argv[2];
const expectedVersion=process.argv[3];
const output=process.argv[4];
if(!exe||!expectedVersion||!output||!fs.existsSync(exe)) throw new Error('Usage: probe-final-native-host.mjs <exe> <version> <output>');
const origin='chrome-extension://aonppfnabjnicjjeoofkfjofolfibggp/';
function request(action){return new Promise((resolve,reject)=>{
  const child=spawn(exe,[origin],{windowsHide:true,stdio:['pipe','pipe','pipe']});
  let bytes=Buffer.alloc(0); const timer=setTimeout(()=>{child.kill();reject(new Error(`${action}: timeout`));},12000);
  child.on('error',error=>{clearTimeout(timer);reject(error);});
  child.stdout.on('data',chunk=>{bytes=Buffer.concat([bytes,chunk]);if(bytes.length<4)return;const length=bytes.readUInt32LE(0);if(bytes.length<length+4)return;clearTimeout(timer);child.kill();resolve(JSON.parse(bytes.subarray(4,4+length).toString('utf8')));});
  const body=Buffer.from(JSON.stringify({action,payload:{}})); const header=Buffer.alloc(4); header.writeUInt32LE(body.length); child.stdin.end(Buffer.concat([header,body]));
});}
const ping=await request('ping'); const capabilities=await request('capabilities');
if(ping.ok!==true||ping.host!=='lat.cacaplay.cacatools.downloadmanager'||ping.appVersion!==expectedVersion) throw new Error(`Unexpected ping: ${JSON.stringify(ping)}`);
if(!['open_player','job_action','set_job_options','list_jobs'].every(action=>capabilities.actions?.includes(action))) throw new Error(`Modern capabilities missing: ${JSON.stringify(capabilities)}`);
const report={at:new Date().toISOString(),exe,sha256:crypto.createHash('sha256').update(fs.readFileSync(exe)).digest('hex'),ping,capabilities};
fs.writeFileSync(output,JSON.stringify(report,null,2)); console.log(JSON.stringify(report));
