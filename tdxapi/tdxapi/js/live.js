// Live tick reader for TdxW.exe V7.73 (verified in-memory layout).
// trade: fn +0x79bd0b, obj=rdi, count=+0x250, data=+0x348  20B <HIIbBII>
// order: fn +0x760a80, obj=arg0, count=+0x254, data=+0x3d0 20B <HIIbcccHI> (only when that window is open)
const base = Process.getModuleByName('TdxW.exe').base;
const NOW_ONLY = %NOW_ONLY%;
const state = {};
function sameBytes(a, b) {
  if (!a || !b || a.byteLength !== b.byteLength) return false;
  const x = new Uint8Array(a), y = new Uint8Array(b);
  for (let i = 0; i < x.length; i++) if (x[i] !== y[i]) return false;
  return true;
}
function handle(kind, o, countOff, dataOff) {
  let code = ''; try { code = o.add(0x68).readPointer().readCString(6); } catch (e) { return; }
  let n; try { n = o.add(countOff).readU32(); } catch (e) { return; }
  let p; try { p = o.add(dataOff).readPointer(); } catch (e) { return; }
  if (p.isNull() || n < 1 || n > 5000000) return;
  const key = kind + ':' + code;
  let st = state[key];
  if (!st) {
    st = state[key] = { count: NOW_ONLY ? n : 0, first: p.readByteArray(20) };
    send({ kind: 'attach', channel: kind, code, count: n, ptr: p.toString() });
  }
  const head = p.readByteArray(20);
  if (!sameBytes(head, st.first)) { st.first = head; send({ kind: 'head_shift', channel: kind, code, count: n }); }
  if (n > st.count) {
    const from = st.count, k = n - st.count;
    send({ kind: 'batch', channel: kind, code, from, to: n, count: n, ptr: p.toString() },
         p.add(from * 20).readByteArray(k * 20));
    st.count = n;
  } else if (n < st.count) {
    send({ kind: 'reset', channel: kind, code, old: st.count, now: n });
    st.count = n;
  }
}
Interceptor.attach(base.add(0x79bd0b), { onEnter(a) { try { handle('trade', this.context.rdi, 0x250, 0x348); } catch (e) { send({ kind: 'err', channel: 'trade', e: String(e) }); } } });
Interceptor.attach(base.add(0x760a80), { onEnter(a) { try { handle('order', a[0], 0x254, 0x3d0); } catch (e) { send({ kind: 'err', channel: 'order', e: String(e) }); } } });
send({ kind: 'ready', base: base.toString() });
