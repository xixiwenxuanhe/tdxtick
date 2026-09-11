const mods=Process.enumerateModules();
const interesting=mods.filter(m=>/ws2|net|ssl|crypto|hq|tdx|l2|push|quote|sock/i.test(m.name));
send({kind:'interesting',mods:interesting.map(m=>m.name+' '+m.base+' size '+m.size)});
send({kind:'count',total:mods.length});
const ws=mods.find(m=>/^ws2_32/i.test(m.name));
if(ws){send({kind:'ws2',base:ws.base.toString(),path:ws.path});
  for(const n of ['recv','WSARecv','recvfrom','WSARecvFrom','select','connect']){
    const a=ws.findExportByName(n); if(a) send({kind:'wsexp',name:n,addr:a.toString()});
  }
}
