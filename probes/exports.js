for(const nm of ['TdxAsioComm64.dll','TDXDeep.dll','TDXRun.dll','tdxRpcx64.dll']){
  try{ const m=Process.getModuleByName(nm);
    const exps=Module.enumerateExportsSync ? Module.enumerateExportsSync(nm) : m.enumerateExports();
    send({kind:'exports',mod:nm,list:exps.map(e=>e.name+'@'+e.address.toString()).slice(0,200)});
  }catch(e){send({kind:'experr',mod:nm,e:String(e)});}
}
