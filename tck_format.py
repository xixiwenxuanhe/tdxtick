"""Decode TDX's 24-byte container and 36-byte replay records."""
import collections, csv, hashlib, json, math, pathlib, struct, zlib
RECORD = struct.Struct("<HIdIIIccII")
START, END = 91500000, 150000999

def load_tck(path):
    blob = pathlib.Path(path).read_bytes()
    if len(blob) < 25:
        raise ValueError("TCK is empty or truncated")
    tag, compressed, uncompressed = struct.unpack_from("<QQQ", blob)
    if compressed != len(blob)-24 or not 0 < uncompressed <= 2_000_000_000:
        raise ValueError("Invalid TCK length header")
    z = zlib.decompressobj()
    data = z.decompress(blob[24:], uncompressed+1)
    if not z.eof or z.unused_data or z.unconsumed_tail or len(data) != uncompressed:
        raise ValueError("TCK decompression length/stream mismatch")
    if len(data) % RECORD.size:
        raise ValueError("Truncated 36-byte record")
    return blob, data, {"header_tag_raw": tag, "compressed_bytes": compressed,
                       "uncompressed_bytes": uncompressed}

def time_string(t):
    ms=t%1000; s=t//1000%100; m=t//100000%100; h=t//10000000
    if not (0<=h<24 and 0<=m<60 and 0<=s<60):
        raise ValueError(f"Invalid HHMMSSmmm: {t}")
    return f"{h:02}:{m:02}:{s:02}.{ms:03}"

def decode(data, code, date, market):
    known={}
    for i, values in enumerate(RECORD.iter_unpack(data)):
        flag,t,price,quantity,channel,sequence,typ,action,bid,ask=values
        typ=typ.decode("ascii"); action=action.decode("ascii")
        if not math.isfinite(price) or price<0:
            raise ValueError(f"Invalid price at source index {i}")
        order_no=0; side=""; order_price=None
        if flag==0 and action in ("B","S"):
            event="order"; side=action
            order_no=(bid if side=="B" else ask) if market==1 else sequence
            known[(channel,side,order_no)]=price
            order_price=price
        elif flag==1 and action=="C":
            event="cancel"
            side="B" if bid else ("S" if ask else "")
            order_no=bid or ask
            order_price=known.get((channel,side,order_no))
        elif flag==1 and action=="0":
            event="trade"
        else:
            event="other"
        yield dict(source_index=i,code=code,date=date,market=market,
            time=time_string(t),time_raw=t,event=event,side=side,
            price_raw=format(price,".10g"),
            order_price="" if order_price is None else format(order_price,".10g"),
            quantity_shares=quantity,channel=channel,sequence=sequence,
            order_number=order_no or "",bid_order_number=bid or "",
            ask_order_number=ask or "",order_type_raw=typ,action_raw=action,
            record_type_raw=flag)

def write_csv(path,rows,columns):
    with pathlib.Path(path).open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=columns);w.writeheader();w.writerows(rows)

def export_tck(source,folder,code,date,market):
    folder=pathlib.Path(folder);folder.mkdir(parents=True,exist_ok=True)
    blob,data,header=load_tck(source)
    rows=list(decode(data,code,date,market))
    if not rows:
        raise ValueError("No replay records returned")
    session=[r for r in rows if START<=r["time_raw"]<=END]
    orders=[r for r in session if r["event"] in ("order","cancel")]
    trades=[r for r in session if r["event"]=="trade"]
    if not orders:
        raise ValueError("No orders/cancellations in 09:15-15:00")
    columns=list(rows[0])
    (folder/"source.tck").write_bytes(blob)
    write_csv(folder/"all_records.csv",rows,columns)
    write_csv(folder/"orders.csv",orders,columns)
    write_csv(folder/"trades.csv",trades,columns)
    summary=dict(code=code,date=date,market=market,**header,
        tck_sha256=hashlib.sha256(blob).hexdigest(),
        raw_sha256=hashlib.sha256(data).hexdigest(),
        total_source_records=len(rows),session_records=len(session),
        orders_and_cancels=len(orders),trades=len(trades),
        events=dict(collections.Counter(r["event"] for r in session)),
        unknown_session_records=sum(r["event"]=="other" for r in session),
        outside_session_records=len(rows)-len(session),
        first_order_time=orders[0]["time"],last_order_time=orders[-1]["time"],
        first_source_time=min(r["time"] for r in rows),
        last_source_time=max(r["time"] for r in rows),
        nonmonotonic_time=sum(a["time_raw"]>b["time_raw"] for a,b in zip(rows,rows[1:])),
        unmatched_cancels=sum(r["event"]=="cancel" and r["order_price"]=="" for r in orders),
        session_start="09:15:00.000",session_end="15:00:00.999",
        coverage_note="All records supplied by TDX in the selected session; exchange-level completeness is not independently certified.")
    (folder/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    return summary

