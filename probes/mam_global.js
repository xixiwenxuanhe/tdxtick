const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const vt=Process.getModuleByName('Viewthem64.dll');
const base=vt.base.add(0x1E0090);
send({kind:'target',addr:base.toString(),rva:'0x1E0090'});
let n=0;
MemoryAccessMonitor.enable({base:base,size:0x2000},{onAccess(d){try{
  if(n>=30) return; n++;
  send({kind:'acc',op:d.operation,from:modof(d.from),addr:d.address.toString()});
}catch(e){send({kind:'inerr',e:String(e)});}}});
send({kind:'monitor_on'});
