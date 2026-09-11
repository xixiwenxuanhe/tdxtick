send({kind:'thread',methods:Object.getOwnPropertyNames(Thread).filter(n=>/watch|break|hardware|backtrace|context/i.test(n))});
send({kind:'frida',version:Frida.version,arch:Process.arch,pointerSize:Process.pointerSize});
const deep=Process.getModuleByName('TDXDeep.dll');
for(const [n,off] of [['TdxDeep_Data',0x34c60],['TdxDeep_Func',0x342b0],['TdxDeep_RegisterCallBackFunc',0x340a0],['TdxDeep_StartInit',0x339a0]]){
  try{
    const a=deep.base.add(off);
    Interceptor.attach(a,{onEnter(args){try{
      send({kind:'deepcall',fn:n,args:[args[0].toString(),args[1].toString(),args[2].toString(),args[3].toString()],
            bt:Thread.backtrace(this.context,Backtracer.ACCURATE).map(x=>{for(const m of Process.enumerateModules()){if(x.compare(m.base)>=0&&x.compare(m.base.add(m.size))<0)return m.name+'+0x'+x.sub(m.base).toString(16);}return x.toString();}).slice(0,6)});
    }catch(e){}}});
    send({kind:'hooked',fn:n,addr:a.toString()});
  }catch(e){send({kind:'hookerr',fn:n,e:String(e)});}
}
