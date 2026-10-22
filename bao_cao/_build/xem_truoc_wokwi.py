# -*- coding: utf-8 -*-
"""Ảnh xem trước diagram.json của Wokwi (không cần mạng): dựng lại sơ đồ trong Chromium.

- Linh kiện có trong @wokwi/elements 1.9.2 (ESP32, MQ-2, quang trở, PIR, DHT22, servo, RGB, LED, trở)
  dùng đúng web component của Wokwi; RC522 dùng board.svg của wokwi-boards; relay và custom chip
  vẽ hộp theo đúng kích thước/chân mà ve_wokwi.py khai báo.
- Dây vẽ bằng cách CHẠY LẠI lệnh h/v/* trong diagram.json từ chân nguồn thật (pinInfo đọc trực tiếp
  từ element đã dựng, xoay quanh tâm khung) rồi nối thẳng tới chân đích → kiểm tra luôn lệnh dây.
- So kích thước/chân đo được với bảng GEO của ve_wokwi.py, in chỗ lệch.

Chạy (Python có playwright):  python xem_truoc_wokwi.py [diagram.json] [ảnh.png]
"""
import json
import os
import sys

import ve_wokwi as vw

HERE = os.path.dirname(os.path.abspath(__file__))
DIAGRAM = sys.argv[1] if len(sys.argv) > 1 else os.path.join(vw.OUT, "diagram.json")
PNG = sys.argv[2] if len(sys.argv) > 2 else os.path.join(vw.OUT, "xem_truoc.png")
BUNDLE = os.path.join(HERE, "assets/wokwi_xem_truoc/wokwi-elements-1.9.2.min.js")
RC522_SVG = os.path.join(HERE, "assets/wokwi/mfrc522.svg")
DX, DY = 40, 70  # dời cả sơ đồ để nhãn ở tọa độ âm vẫn hiện

PAGE = r"""<!doctype html><html><head><meta charset="utf-8">
<style>
 body{margin:0;background:#fff;font-family:"DejaVu Sans",sans-serif}
 #c{position:relative;width:__W__px;height:__H__px}
 .part{position:absolute;display:flex;transform-origin:center}
 .box{box-sizing:border-box;border-radius:3px;color:#fff;font-size:8px;display:flex;
      align-items:center;justify-content:center;text-align:center;line-height:1.1}
 .chip{background:#087f45}
 .relay{background:#2952a3}
 .hole{position:absolute;width:5px;height:5px;margin:-2.5px 0 0 -2.5px;border-radius:50%;background:#ffe680}
 .txt{position:absolute;white-space:pre-line;width:max-content;color:#000}
 svg#w{position:absolute;left:0;top:0;pointer-events:none}
</style></head><body><div id="c"></div>
<svg id="w" width="__W__" height="__H__"></svg>
<script src="file://__BUNDLE__"></script>
<script>
const D = __DIAGRAM__, GEO = __GEO__, DX = __DX__, DY = __DY__;
const c = document.getElementById('c');
const els = {}, report = [];
function place(el, p){ el.classList.add('part'); el.style.left=(p.left+DX)+'px'; el.style.top=(p.top+DY)+'px'; }
for (const p of D.parts){
  if (p.type === 'wokwi-text'){
    const t=document.createElement('div'); t.className='txt'; t.textContent=p.attrs.text;
    t.style.left=(p.left+DX)+'px'; t.style.top=(p.top+DY)+'px'; t.style.fontSize=(p.attrs.fontSize||14)+'px';
    c.appendChild(t); continue;
  }
  let el;
  if (p.type.startsWith('wokwi-') && customElements.get(p.type)){
    el=document.createElement(p.type);
    for (const [k,v] of Object.entries(p.attrs||{})){
      if (k==='flip') el.flip = v==='1'; else el.setAttribute(k,v);
    }
  } else if (p.type==='board-mfrc522'){
    el=document.createElement('img'); el.src='file://__RC522__';
    el.style.width=GEO[p.type][0]+'px'; el.style.height=GEO[p.type][1]+'px';
  } else {
    const g=GEO[p.type]; el=document.createElement('div');
    el.className='box '+(p.type.startsWith('chip-')?'chip':'relay');
    el.style.width=g[0]+'px'; el.style.height=g[1]+'px';
    el.textContent = p.type.startsWith('chip-') ? (__CHIPNAMES__[p.type]||p.type) : 'Relay (mức THẤP)';
    for (const [n,[x,y]] of Object.entries(g[2])){
      const h=document.createElement('div'); h.className='hole'; h.style.left=x+'px'; h.style.top=y+'px'; el.appendChild(h);
    }
  }
  place(el,p); c.appendChild(el); els[p.id]={el,p};
}
function pinXY(id,pin){
  const {el,p}=els[id]; const w=el.offsetWidth, h=el.offsetHeight;
  let x,y;
  if (el.pinInfo){ const pi=el.pinInfo.find(q=>q.name===pin); if(!pi){report.push('Không có chân '+id+':'+pin); return [0,0];} x=pi.x; y=pi.y; }
  else { [x,y]=GEO[p.type][2][pin]; }
  const a=(p.rotate||0)*Math.PI/180, dx=x-w/2, dy=y-h/2;
  return [p.left+DX+w/2+dx*Math.cos(a)-dy*Math.sin(a), p.top+DY+h/2+dx*Math.sin(a)+dy*Math.cos(a)];
}
window.render = function(){
  // 1. Kích thước & chân đo được so với GEO
  for (const [id,{el,p}] of Object.entries(els)){
    const g=GEO[p.type]; if(!g) continue;
    if (Math.abs(el.offsetWidth-g[0])>0.6 || Math.abs(el.offsetHeight-g[1])>0.6)
      report.push(`Khung ${id} (${p.type}): đo ${el.offsetWidth}×${el.offsetHeight}, GEO ${g[0].toFixed(2)}×${g[1].toFixed(2)}`);
    if (el.pinInfo) for (const [n,[x,y]] of Object.entries(g[2])){
      const pi=el.pinInfo.find(q=>q.name===n);
      if(!pi) report.push(`GEO có chân ${p.type}:${n} mà element không có`);
      else if (Math.abs(pi.x-x)>0.05||Math.abs(pi.y-y)>0.05) report.push(`Chân ${p.type}:${n} element (${pi.x},${pi.y}) ≠ GEO (${x},${y})`);
    }
  }
  for (const id of Object.keys(els)) els[id].el.style.transform = `rotate(${els[id].p.rotate||0}deg)`;
  // 2. Dây theo lệnh h/v/* (Wokwi: lệnh trước * tính từ chân nguồn, sau * tính ngược từ chân đích)
  const svg=document.getElementById('w'); let html='';
  for (const [a,b,color,ins] of D.connections){
    const [ia,pa]=a.split(':'), [ib,pb]=b.split(':');
    let [x,y]=pinXY(ia,pa); const head=[[x,y]];
    const star=ins.indexOf('*'), pre=star<0?ins:ins.slice(0,star), post=star<0?[]:ins.slice(star+1);
    for (const s of pre){ const v=parseFloat(s.slice(1)); if(s[0]==='h') x+=v; else y+=v; head.push([x,y]); }
    let [tx,ty]=pinXY(ib,pb); const tail=[[tx,ty]];
    for (const s of post.slice().reverse()){ const v=parseFloat(s.slice(1)); if(s[0]==='h') tx+=v; else ty+=v; tail.push([tx,ty]); }
    if (Math.abs(x-tx)>0.5 && Math.abs(y-ty)>0.5){ report.push(`Đoạn tự nối bị gấp: ${a} → ${b} (${x.toFixed(1)},${y.toFixed(1)})→(${tx.toFixed(1)},${ty.toFixed(1)})`); head.push([tx,y]); }
    const pts=head.concat(tail.reverse());
    const d=pts.map((q,i)=>(i?'L':'M')+q[0].toFixed(2)+' '+q[1].toFixed(2)).join(' ');
    html+=`<path d="${d}" fill="none" stroke="#fff" stroke-width="3.6" stroke-linejoin="round" opacity=".9"/>`+
          `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.8" stroke-linejoin="round"/>`+
          `<circle cx="${pts[0][0]}" cy="${pts[0][1]}" r="1.6" fill="${color}"/><circle cx="${pts[pts.length-1][0]}" cy="${pts[pts.length-1][1]}" r="1.6" fill="${color}"/>`;
  }
  svg.innerHTML=html;
  return report;
};
</script></body></html>"""


def main():
    from playwright.sync_api import sync_playwright

    with open(DIAGRAM, encoding="utf-8") as f:
        diagram = json.load(f)
    xs = [p["left"] for p in diagram["parts"]]
    ys = [p["top"] for p in diagram["parts"]]
    w, h = int(max(xs) + 320 + DX), int(max(ys) + 120 + DY)
    geo = {k: [v[0], v[1], {n: list(xy) for n, xy in v[2].items()}] for k, v in vw.GEO.items()}
    names = {"chip-" + k: t for k, (t, _) in vw.CHIPS.items()}
    html = (PAGE.replace("__DIAGRAM__", json.dumps(diagram, ensure_ascii=False))
            .replace("__GEO__", json.dumps(geo)).replace("__CHIPNAMES__", json.dumps(names, ensure_ascii=False))
            .replace("__BUNDLE__", BUNDLE).replace("__RC522__", RC522_SVG)
            .replace("__DX__", str(DX)).replace("__DY__", str(DY))
            .replace("__W__", str(w)).replace("__H__", str(h)))
    tmp = os.path.join(os.path.dirname(PNG), "_xem_truoc.html")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(html)
    try:
        with sync_playwright() as pw:
            b = pw.chromium.launch(args=["--allow-file-access-from-files"])
            pg = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            pg.goto("file://" + tmp)
            pg.wait_for_function("customElements.get('wokwi-esp32-devkit-v1') !== undefined")
            pg.wait_for_timeout(800)
            report = pg.evaluate("window.render()")
            pg.wait_for_timeout(300)
            pg.screenshot(path=PNG, full_page=True)
            b.close()
    finally:
        os.remove(tmp)
    for r in report:
        print("LỆCH:", r)
    print(f"Ảnh: {PNG} ({w}×{h} px CSS, ×2) — {len(report)} chỗ lệch")


if __name__ == "__main__":
    main()
