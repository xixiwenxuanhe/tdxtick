const MODS=Process.enumerateModules();
function modof(a){try{const x=ptr(a);for(const m of MODS){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}}catch(e){} return String(a);}
const TdxW=Process.getModuleByName('TdxW.exe');
let done=false;
Interceptor.attach(TdxW.base.add(0x79bd0b),{onEnter(a){try{
  if(done) return; done=true;
  const o=this.context.rdi; const vt=o.readPointer();
  const out=[];
  for(let i=0;i<80;i++){ try{ const fn=vt.add(i*8).readPointer();
    if(fn.isNull()) { out.push(i+'=null'); continue; }
    out.push(i+'='+modof(fn));
    if(modof(fn).startsWith('TdxW.exe')){
      let c=0; try{ Interceptor.attach(fn,{onEnter(){c++;}}); }catch(e){}
      counts[i]={c:()=>c,addr:modof(fn)};
    }
  }catch(e){break;} }
  send({kind:'vtable',code:o.add(0x68).readPointer().readCString(6),entries:out});
  setTimeout(()=>{ const r=Object.keys(counts).map(k=>k+':'+counts[k].addr+':'+counts[k].c()); send({kind:'counts',r}); },12000);
}catch(e){send({kind:'err',e:String(e)});}}});
var counts={};
send({kind:'ready'});
