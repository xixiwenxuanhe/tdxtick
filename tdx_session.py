"""Version-checked access to TDX's own historical file loader on its UI thread."""
import ctypes, datetime as dt, hashlib, json, pathlib, threading, time, uuid
from ctypes import wintypes as W
import frida
BUILD_SHA256="58bd2117ec86e8c063639f7adae4218011bb93998e3d93dcd286672d1978736b"
HISTORY_RVA=0x213d50
JS=r"""
const main=Process.getModuleByName('TdxW.exe');
const request=new NativeFunction(main.base.add(0x213d50),'pointer',
                                ['uint8','pointer','int','pointer']);
const crt=Process.getModuleByName('MSVCR100.dll');
const fclose=new NativeFunction(crt.getExportByName('fclose'),'int',['pointer']);
const user=Process.getModuleByName('USER32.dll');
const post=new NativeFunction(user.getExportByName('PostMessageW'),'bool',
                             ['pointer','uint','pointer','pointer']);
let pending=null,active=false;
function safeSend(x){send(x);}
for(const n of ['DispatchMessageW','DispatchMessageA']){
 Interceptor.attach(user.getExportByName(n),{onEnter(a){
  if(!pending || a[0].readPointer().toString()!==pending.hwnd ||
     a[0].add(8).readU32()!==0x83f1 || a[0].add(16).readU64().toString()!=='5522517')return;
  const q=pending;pending=null;active=true;
  safeSend({kind:'executing',thread_id:Process.getCurrentThreadId()});
  try {
   const code=Memory.allocUtf8String(q.code),ext=Memory.allocUtf8String('tck');
   const file=request(q.market,code,q.date,ext);
   const ok=!file.isNull();
   if(ok)fclose(file);
   active=false;safeSend({kind:'done',ok});
  }catch(e){active=false;safeSend({kind:'failed',error:String(e)});}
 }});
}
rpc.exports={
 queue(q){
  if(pending||active)throw new Error('Download already active');
  pending=q;
  if(!post(ptr(q.hwnd),0x83f1,ptr(5522517),ptr(0))){pending=null;return false;}
  return true;
 },
 cancelPending(){if(active)return false;pending=null;return true;}
};
"""

def find_process(pid=None):
    candidates=[p for p in frida.get_local_device().enumerate_processes()
                if p.name.lower()=="tdxw.exe" and (pid is None or p.pid==pid)]
    if len(candidates)!=1:
        raise RuntimeError("请启动并登录通达信；若开了多个实例，请使用 --pid 指定进程。")
    return candidates[0].pid

def executable_path(pid):
    k=ctypes.WinDLL("kernel32",use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.QueryFullProcessImageNameW.argtypes=[W.HANDLE,W.DWORD,W.LPWSTR,ctypes.POINTER(W.DWORD)]
    k.CloseHandle.argtypes=[W.HANDLE]
    h=k.OpenProcess(0x1000,False,pid)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    try:
        b=ctypes.create_unicode_buffer(32768);n=W.DWORD(len(b))
        if not k.QueryFullProcessImageNameW(h,0,b,ctypes.byref(n)):
            raise ctypes.WinError(ctypes.get_last_error())
        return pathlib.Path(b.value)
    finally:k.CloseHandle(h)

def main_window(pid):
    u=ctypes.WinDLL("user32")
    u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
    u.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
    u.IsWindowVisible.argtypes=[W.HWND]
    u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,ctypes.c_int]
    windows=[]
    @ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
    def callback(h,l):
        p=W.DWORD();u.GetWindowThreadProcessId(h,ctypes.byref(p))
        if p.value==pid and u.IsWindowVisible(h):
            r=W.RECT();u.GetWindowRect(h,ctypes.byref(r))
            windows.append(((r.right-r.left)*(r.bottom-r.top),int(h)))
        return True
    u.EnumWindows(callback,0)
    if not windows:raise RuntimeError("找不到通达信主窗口；请先完成登录。")
    return max(windows)[1]

def download(code,date,market,pid=None,progress=print):
    pid=find_process(pid)
    exe=executable_path(pid)
    digest=hashlib.sha256(exe.read_bytes()).hexdigest()
    if digest!=BUILD_SHA256:
        raise RuntimeError("通达信程序版本与已验证版本不同，停止调用内部地址。需要重新适配。")
    hwnd=main_window(pid)
    cache=exe.parent/"T0002"/"zst_cache"/f"{'sh' if market==1 else 'sz'}{code}_{date}.tck"
    # An OS lock prevents concurrent requests through the client's shared downloader.
    import msvcrt
    lock=exe.parent/"T0002"/"codex_tck_download.lock"
    with lock.open("a+b") as guard:
        if guard.seek(0,2)==0:guard.write(b"0");guard.flush()
        guard.seek(0)
        try:msvcrt.locking(guard.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:raise RuntimeError("另一个导出任务正在使用通达信，请稍后重试。")
        session=None;script=None;preclose_backup=None
        terminal=threading.Event();started=threading.Event();result={}
        try:
            cn=dt.timezone(dt.timedelta(hours=8))
            close=dt.datetime.strptime(date,"%Y%m%d").replace(hour=15,minute=1,tzinfo=cn)
            if cache.exists() and cache.stat().st_mtime<close.timestamp():
                preclose_backup=cache.with_name(cache.name+".preclose-"+uuid.uuid4().hex)
                cache.rename(preclose_backup)
            session=frida.attach(pid)
            def detached(reason,crash=None):
                if not terminal.is_set():
                    result.update(error=f"通达信连接已断开：{reason}")
                    terminal.set()
            session.on("detached",detached)
            def receive(message,data):
                if message.get("type")=="error":
                    result.update(error=message.get("description",str(message)))
                    terminal.set()
                    return
                payload=message.get("payload",{})
                if payload.get("kind")=="executing":
                    started.set()
                elif payload.get("kind") in ("done","failed"):
                    result.update(payload);terminal.set()
            script=session.create_script(JS);script.on("message",receive);script.load()
            if not script.exports_sync.queue(dict(code=code,date=int(date),market=market,hwnd=hex(hwnd))):
                raise RuntimeError("无法把请求送入通达信主线程。")
            begun=time.monotonic()
            while not terminal.wait(10):
                elapsed=int(time.monotonic()-begun)
                progress(f"通达信正在获取 {code} / {date}，已等待 {elapsed} 秒。",flush=True)
                if not started.is_set() and elapsed>=30:
                    script.exports_sync.cancel_pending()
                    raise TimeoutError("通达信主线程没有响应；请检查是否有登录或其他弹窗。")
                # The native loader handles its own timeout. Do not detach mid-call.
            if result.get("error"):
                raise RuntimeError(result["error"])
            if not result.get("ok") or not cache.is_file() or cache.stat().st_size<=24:
                raise RuntimeError(f"通达信未提供 {code} / {date} 的逐笔文件。可能是非交易日、停牌、超出历史范围或当前账号无该数据。")
            return cache,dict(pid=pid,exe=str(exe),exe_sha256=digest,loader_rva=hex(HISTORY_RVA),
                             preclose_cache_backup=str(preclose_backup) if preclose_backup else None,
                             request_date=date,request_code=code,request_market=market)
        finally:
            if script and started.is_set() and not terminal.is_set():
                progress("等待通达信原生请求返回后再退出……",flush=True)
                terminal.wait()
            if session:session.detach()
            if preclose_backup and not result.get("ok") and not cache.exists():
                preclose_backup.rename(cache)
            guard.seek(0);msvcrt.locking(guard.fileno(),msvcrt.LK_UNLCK,1)
