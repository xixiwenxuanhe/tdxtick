import ctypes
from ctypes import wintypes as W
u=ctypes.WinDLL('user32')
u.GetWindowThreadProcessId.argtypes=[W.HWND,ctypes.POINTER(W.DWORD)]
u.IsWindowVisible.argtypes=[W.HWND]
u.GetWindowTextW.argtypes=[W.HWND,W.LPWSTR,ctypes.c_int]
u.GetWindowRect.argtypes=[W.HWND,ctypes.POINTER(W.RECT)]
import sys
pids=set(int(x) for x in sys.argv[1:])
res=[]
@ctypes.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
def cb(h,l):
    p=W.DWORD(); u.GetWindowThreadProcessId(h,ctypes.byref(p))
    if p.value in pids and u.IsWindowVisible(h):
        b=ctypes.create_unicode_buffer(512); u.GetWindowTextW(h,b,512)
        r=W.RECT(); u.GetWindowRect(h,ctypes.byref(r))
        res.append((p.value,b.value,(r.left,r.top,r.right,r.bottom)))
    return True
u.EnumWindows(cb,0)
for pid,t,rect in res: print(pid,rect,repr(t))
