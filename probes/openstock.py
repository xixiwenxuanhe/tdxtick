import ctypes, sys, time
from ctypes import wintypes as W
u=ctypes.WinDLL('user32')
u.EnumWindows.argtypes=[ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM),W.LPARAM]
u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
u.IsWindowVisible.argtypes=[W.HWND]; u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,ctypes.c_int]
u.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
u.ShowWindow.argtypes=[W.HWND,ctypes.c_int]; u.SetForegroundWindow.argtypes=[W.HWND]
pid=int(sys.argv[1]); code=sys.argv[2]
cands=[]
@ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
def cb(h,l):
    p=W.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(p))
    if p.value==pid and u.IsWindowVisible(h):
        r=W.RECT(); u.GetWindowRect(h,ctypes.byref(r))
        cands.append(((r.right-r.left)*(r.bottom-r.top),h))
    return True
u.EnumWindows(cb,0)
cands.sort(reverse=True)
hwnd=cands[0][1]
print("hwnd",hwnd,"cands",len(cands))
u.ShowWindow(hwnd,9)  # SW_RESTORE
u.SetForegroundWindow(hwnd)
time.sleep(0.4)
VK={c:0x30+i for i,c in enumerate('0123456789')}; VK['\r']=0x0D
for ch in code+'\r':
    vk=VK[ch]
    u.keybd_event(vk,0,0,0); time.sleep(0.03)
    u.keybd_event(vk,0,2,0); time.sleep(0.03)
print("sent",code)
