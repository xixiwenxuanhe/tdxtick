const deep=Process.getModuleByName('TDXDeep.dll');
const reg=deep.findExportByName('TdxDeep_RegisterCallBackFunc');
send({kind:'deep',reg:reg?reg.toString():null,data:deep.findExportByName('TdxDeep_Data').toString(),func:deep.findExportByName('TdxDeep_Func').toString()});
let cb=null;
if(reg) Interceptor.attach(reg,{onEnter(args){try{
  send({kind:'register',a0:args[0].toString(),a1:args[1].toString(),a2:args[2].toString()});
  // hook the callback pointer candidates
  for(const i of [0,1,2]){
    const p=args[i];
    if(p.compare(ptr('0x10000'))>0 && p.compare(ptr('0x7fffffffffff'))<0 && !cb){
      cb=p; send({kind:'hooking',idx:i,addr:p.toString()});
      try{ Interceptor.attach(p,{onEnter(a){send({kind:'cb',idx:i,args:[a[0].toString(),a[1].toString(),a[2].toString(),a[3].toString()]});}}); }catch(e){send({kind:'hookerr',e:String(e)});}
    }
  }
}catch(e){send({kind:'regerr',e:String(e)});}}});
send({kind:'ready'});
