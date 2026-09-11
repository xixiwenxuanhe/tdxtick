const base=Process.getModuleByName('TdxW.exe').base;
let sent=false;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(sent)return; sent=true;
  const o=this.context.rdi;
  const code=o.add(0x68).readPointer().readCString(6);
  const cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  send({kind:'meta',code,obj:o.toString(),count:cnt,ptr:p.toString()});
  send({kind:'dump',obj:o.toString()}, o.readByteArray(0x600));
  const st=o.add(0x68).readPointer();
  send({kind:'state',st:st.toString()}, st.readByteArray(0x200));
  // find pointer-looking values in the object and dump target heads
  const cands=[];
  for(let off=0; off<0x600; off+=8){
    try{ const v=o.add(off).readPointer();
      if(v.compare(ptr('0x10000'))>0 && v.compare(ptr('0x7fffffffffff'))<0){
        cands.push({off,val:v.toString()});
      }
    }catch(e){}
  }
  send({kind:'cands',cands:cands.slice(0,80)});
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});
