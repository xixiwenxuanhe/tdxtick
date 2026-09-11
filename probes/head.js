const base=Process.getModuleByName('TdxW.exe').base;
const s=Process.getModuleByName('ntdll.dll');
let sent=false;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(sent)return; sent=true;
  const o=this.context.rdi;
  const code=o.add(0x68).readPointer().readCString(6);
  const cnt=o.add(0x250).readU32(), p=o.add(0x348).readPointer();
  const first=p.readByteArray(20);
  const last=p.add((cnt-1)*20).readByteArray(20);
  send({kind:'head',code,count:cnt,ptr:p.toString()},first);
  send({kind:'tail'},last);
}catch(e){send({kind:'err',e:String(e)});}}});
send({kind:'ready'});
