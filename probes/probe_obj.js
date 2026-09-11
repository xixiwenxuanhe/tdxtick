const base=Process.getModuleByName('TdxW.exe').base;
let sent=0;
Interceptor.attach(base.add(0x79bd0b),{onEnter(a){try{
  if(sent>=3) return;
  const o=this.context.rdi;
  let code=''; try{code=o.add(0x68).readPointer().readCString(6);}catch(e){}
  let nt=-1,pt=null,no=-1,po=null;
  try{nt=o.add(0x250).readU32();}catch(e){}
  try{pt=o.add(0x348).readPointer();}catch(e){}
  try{no=o.add(0x254).readU32();}catch(e){}
  try{po=o.add(0x3d0).readPointer();}catch(e){}
  send({kind:'obj',n:sent,code,obj:o.toString(),
        trade_count:nt,trade_ptr:pt?pt.toString():'?',
        order_count:no,order_ptr:po?po.toString():'?'});
  try{ if(pt&&!pt.isNull()&&nt>0&&nt<1000000){send({kind:'trade_head',n:sent},pt.readByteArray(Math.min(nt,3)*20));} }catch(e){send({kind:'errT',e:String(e)});}
  try{ if(po&&!po.isNull()&&no>0&&no<1000000){send({kind:'order_head',n:sent},po.readByteArray(Math.min(no,3)*20));} }catch(e){send({kind:'errO',e:String(e)});}
  sent++;
}catch(e){send({kind:'outer',e:String(e)});}}});
send({kind:'ready'});
