const base=Process.getModuleByName('TdxW.exe').base;
let sent=false;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(sent)return; sent=true;
  const o=this.context.rdi;
  const code=o.add(0x68).readPointer().readCString(6);
  for(const off of [0x340,0x348,0x350,0x358,0x360,0x368]){
    try{
      const p=o.add(off).readPointer();
      if(p.isNull()){ send({kind:'null',off:off.toString()}); continue; }
      send({kind:'buf',off:off.toString(),ptr:p.toString()}, p.readByteArray(0x100));
    }catch(e){ send({kind:'buferr',off:off.toString(),e:String(e)}); }
  }
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});
