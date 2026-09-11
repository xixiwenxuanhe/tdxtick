const base=Process.getModuleByName('TdxW.exe').base;
let vt=null;
function doScan(){
  if(!vt){send({kind:'novt'});return;}
  let h=vt.toString().slice(2); while(h.length<16) h='0'+h;
  let bytes=[]; for(let i=0;i<16;i+=2) bytes.push(h.substr(i,2));
  bytes.reverse();
  const pattern=bytes.join(' ');
  send({kind:'pattern',vt:vt.toString(),pattern});
  const ranges=Process.enumerateRanges('rw-').filter(r=>r.base.compare(ptr('0x80000000'))<0 && r.size<0x20000000);
  send({kind:'ranges',n:ranges.length,bytes:ranges.reduce((a,r)=>a+r.size,0)});
  let hits=[];
  for(const r of ranges){
    try{ const res=Memory.scanSync(r.base,r.size,pattern);
      for(const m of res) hits.push(m.address.toString());
    }catch(e){}
  }
  send({kind:'hits',hits});
  for(const h of hits.slice(0,40)){
    try{ const o=ptr(h);
      let code=''; try{code=o.add(0x68).readPointer().readCString(6);}catch(e){}
      let cnt=0,ptrv=null; try{cnt=o.add(0x250).readU32();}catch(e){} try{ptrv=o.add(0x348).readPointer();}catch(e){}
      send({kind:'inst',obj:h,code,count:cnt,ptr:ptrv?ptrv.toString():null});
    }catch(e){}
  }
}
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){ if(vt)return; try{ vt=this.context.rdi.readPointer(); }catch(e){}
  setTimeout(doScan,0); }});
send({kind:'ready'});
