/* ============ Charts — dependency-free SVG charts ============ */
const Charts = {
  palette:['#4f46e5','#7c3aed','#0284c7','#16a34a','#d97706','#dc2626','#0891b2'],
  colors(n){ return Array.from({length:n},(_,i)=>this.palette[i%this.palette.length]); },
  line(el, labels, series, opt={}) {
    const w = el.clientWidth || 520, h = opt.h || 190, pad = {l:38,r:12,t:12,b:22};
    const all = series.flatMap(s=>s.data); const max = Math.max(...all)*1.15 || 1, min = 0;
    const iw = w-pad.l-pad.r, ih = h-pad.t-pad.b;
    const X = i => pad.l + (i/(labels.length-1))*iw;
    const Y = v => pad.t + ih - ((v-min)/(max-min))*ih;
    let g = '';
    for (let i=0;i<=4;i++){ const yv = min + (max-min)*i/4, y = Y(yv);
      g += `<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="#e2e8f0"/>
            <text x="${pad.l-6}" y="${y+3}" text-anchor="end" font-size="9" fill="#94a3b8">${Math.round(yv).toLocaleString()}</text>`; }
    labels.forEach((lb,i)=>{ if (labels.length>8 && i%Math.ceil(labels.length/7)!==0) return;
      g += `<text x="${X(i)}" y="${h-6}" text-anchor="middle" font-size="9" fill="#94a3b8">${lb}</text>`; });
    series.forEach((s,si)=>{ const pts = s.data.map((v,i)=>`${X(i)},${Y(v)}`).join(' ');
      g += `<polyline points="${pts}" fill="none" stroke="${s.color||this.palette[si]}" stroke-width="2" ${s.dash?'stroke-dasharray="5 3"':''}/>`;
      if (!opt.noDots) s.data.forEach((v,i)=>{ g += `<circle cx="${X(i)}" cy="${Y(v)}" r="2.5" fill="${s.color||this.palette[si]}"/>`; }); });
    el.innerHTML = `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}">${g}</svg>`
      + (opt.legend!==false ? `<div class="flex wrap" style="justify-content:center;gap:12px;font-size:10.5px;color:var(--text-2);margin-top:4px">${series.map((s,i)=>`<span><span class="dot-ic" style="background:${s.color||this.palette[i]}"></span>${s.name}</span>`).join('')}</div>` : '');
  },
  bar(el, labels, values, opt={}) {
    const w = el.clientWidth || 480, h = opt.h || 190, pad = {l:36,r:10,t:10,b:22};
    const max = Math.max(...values)*1.15 || 1, iw = w-pad.l-pad.r, ih = h-pad.t-pad.b;
    const bw = Math.min(30, iw/labels.length*0.55), gap = iw/labels.length;
    let g = '';
    for (let i=0;i<=3;i++){ const yv = max*i/3, y = pad.t+ih-(yv/max)*ih;
      g += `<line x1="${pad.l}" y1="${y}" x2="${w-pad.r}" y2="${y}" stroke="#e2e8f0"/>
            <text x="${pad.l-5}" y="${y+3}" text-anchor="end" font-size="9" fill="#94a3b8">${Math.round(yv).toLocaleString()}</text>`; }
    labels.forEach((lb,i)=>{ const v = values[i], bh = (v/max)*ih, x = pad.l+i*gap+(gap-bw)/2, y = pad.t+ih-bh;
      const c = opt.colors ? opt.colors[i] : this.palette[0];
      g += `<rect x="${x}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${c}"><title>${lb}: ${v}</title></rect>
            <text x="${x+bw/2}" y="${h-6}" text-anchor="middle" font-size="9" fill="#94a3b8">${lb}</text>`; });
    el.innerHTML = `<svg width="100%" height="${h}" viewBox="0 0 ${w} ${h}">${g}</svg>`;
  },
  hbar(el, labels, values, opt={}) {
    const max = Math.max(...values)*1.1 || 1;
    el.innerHTML = labels.map((lb,i)=>`<div style="display:flex;align-items:center;gap:8px;font-size:11.5px;margin-bottom:7px">
      <span style="width:70px;color:var(--text-2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${lb}</span>
      <div style="flex:1;height:14px;background:#f1f5f9;border-radius:7px;overflow:hidden">
        <div style="width:${(values[i]/max)*100}%;height:100%;background:${this.palette[i%6]};border-radius:7px"></div></div>
      <b style="width:56px;text-align:right">${opt.fmt?opt.fmt(values[i]):values[i].toLocaleString()}</b></div>`).join('');
  },
  pie(el, labels, values, opt={}) {
    const total = values.reduce((a,b)=>a+b,0)||1;
    const cx=cy=(opt.h||170)/2, r=cy-16, r2=r*0.62; let a0=-Math.PI/2, g='';
    values.forEach((v,i)=>{ const frac=v/total, a1=a0+frac*Math.PI*2;
      const large = frac>0.5?1:0;
      const x0=cx+r*Math.cos(a0), y0=cy+r*Math.sin(a0), x1=cx+r*Math.cos(a1), y1=cy+r*Math.sin(a1);
      const x2=cx+r2*Math.cos(a1), y2=cy+r2*Math.sin(a1), x3=cx+r2*Math.cos(a0), y3=cy+r2*Math.sin(a0);
      g += `<path d="M${x0},${y0} A${r},${r} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${r2},${r2} 0 ${large} 0 ${x3},${y3} Z"
        fill="${this.palette[i%6]}"><title>${labels[i]}: ${v} (${(frac*100).toFixed(1)}%)</title></path>`;
      a0=a1; });
    el.innerHTML = `<svg width="100%" height="${opt.h||170}" viewBox="0 0 ${opt.h||170} ${opt.h||170}">${g}
      <text x="${cx}" y="${cy-2}" text-anchor="middle" font-size="15" font-weight="700" fill="#0f172a">${total.toLocaleString()}</text>
      <text x="${cx}" y="${cy+13}" text-anchor="middle" font-size="9" fill="#94a3b8">总计</text></svg>
      <div class="flex wrap" style="justify-content:center;gap:10px;font-size:10.5px;margin-top:2px">
      ${labels.map((lb,i)=>`<span><span class="dot-ic" style="background:${this.palette[i%6]}"></span>${lb} ${(values[i]/total*100).toFixed(0)}%</span>`).join('')}</div>`;
  },
  gauge(el, val, opt={}) {
    const max=100, r=64, cx=cy=75, a0=Math.PI*0.75, a1=a0+(val/max)*Math.PI*1.5;
    const arc=(a,b,rr,w,color)=>{ const x0=cx+rr*Math.cos(a),y0=cy+rr*Math.sin(a),x1=cx+rr*Math.cos(b),y1=cy+rr*Math.sin(b);
      return `<path d="M${x0},${y0} A${rr},${rr} 0 ${b-a>Math.PI?1:0} 1 ${x1},${y1}" stroke="${color}" stroke-width="${w}" fill="none" stroke-linecap="round"/>`; };
    el.innerHTML = `<svg width="100%" height="130" viewBox="0 0 150 130">
      ${arc(a0, a0+Math.PI*1.5, r, 13, '#e2e8f0')}${arc(a0, a1, r, 13, val>80?'#16a34a':val>60?'#4f46e5':'#d97706')}
      <text x="${cx}" y="${cy+8}" text-anchor="middle" font-size="24" font-weight="800" fill="#0f172a">${val}%</text>
      <text x="${cx}" y="${cy+24}" text-anchor="middle" font-size="9.5" fill="#94a3b8">${opt.label||''}</text></svg>`;
  },
  spark(el, data, color='#4f46e5') {
    const w=120,h=32,max=Math.max(...data),min=Math.min(...data);
    const pts = data.map((v,i)=>`${(i/(data.length-1))*w},${h-2-((v-min)/(max-min||1))*(h-6)}`).join(' ');
    el.innerHTML = `<svg width="${w}" height="${h}"><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.8"/></svg>`;
  },
};
