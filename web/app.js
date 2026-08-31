const fileInput = document.getElementById('fileInput');
const dropZone = document.getElementById('dropZone');
const pickBtn = document.getElementById('pickBtn');
const tbody = document.getElementById('tbody');
const countEl = document.getElementById('count');
const clearBtn = document.getElementById('clearBtn');
const copyAllBtn = document.getElementById('copyAllBtn');
const openAllVtBtn = document.getElementById('openAllVtBtn');
const checkAllApiBtn = document.getElementById('checkAllApiBtn');
const scanAllLocalBtn = document.getElementById('scanAllLocalBtn');
const localHealthEl = document.getElementById('localHealth');
const localHealthText = document.getElementById('localHealthText');
const localHealthDetail = document.getElementById('localHealthDetail');
const localDot = document.getElementById('localDot');
const apiKeyInput = document.getElementById('apiKey');
const serverDot = document.getElementById('serverDot');

let files = [];
let isSelecting = false;
let pendingRender = false;
// Detecta seleção/mouse para pausar re-render e não quebrar seleção do hash
document.addEventListener('mousedown', ()=>{ isSelecting = true; });
document.addEventListener('mouseup', ()=>{ setTimeout(()=>{ isSelecting = false; if(pendingRender){ pendingRender=false; render(); } }, 250); });
document.addEventListener('selectionchange', ()=>{
  const sel = window.getSelection();
  const hasSel = sel && sel.toString().length>0 && document.activeElement && document.activeElement.closest && !document.activeElement.closest('input');
  if(hasSel){ isSelecting = true; }
  else if(!hasSel && isSelecting){
    // só libera após mouseup, mas se seleção foi limpa via teclado, libera em 300ms
    setTimeout(()=>{ if(!window.getSelection() || window.getSelection().toString().length===0){ isSelecting=false; if(pendingRender){pendingRender=false; render();} } }, 300);
  }
});

function formatBytes(b){ if(!b) return '0 B'; const k=1024,s=['B','KB','MB','GB'], i=Math.floor(Math.log(b)/Math.log(k)); return parseFloat((b/Math.pow(k,i)).toFixed(2))+' '+s[i]; }
function escapeHtml(s){ return s.replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function updateRowProgress(id){
  // Atualiza só a barra do row sem recriar tabela (preserva seleção)
  const entry = files.find(x=>x.id===id);
  if(!entry) return;
  const row = document.querySelector(`tr[data-fid="${id}"]`);
  if(!row) return;
  const fill = row.querySelector('.progress-fill');
  if(fill && entry.progress!=null) fill.style.width = Math.round(entry.progress*100)+'%';
  const status = row.querySelector('.hashing-status');
  if(status && entry.progress!=null) status.textContent = `⏳ ${Math.round(entry.progress*100)}%` + (entry.size>50*1024*1024 ? ` (${formatBytes(entry.hashed||0)} / ${formatBytes(entry.size)})` : '');
  const localFill = row.querySelector('.local-progress');
  if(localFill && entry.local?.uploadProgress!=null) localFill.style.width = Math.round(entry.local.uploadProgress*100)+'%';
  const localStatus = row.querySelector('.local-status');
  if(localStatus && entry.local?.startTime){
    const elapsed = ((Date.now()-entry.local.startTime)/1000).toFixed(1);
    const pct = Math.round(entry.local.uploadProgress*100);
    const phase = pct<70 ? 'enviando' : (pct<95 ? 'scan' : 'fim');
    localStatus.textContent = `⏳ ${phase} ${elapsed}s`;
  }
}

function updateToolbar(){
  const done = files.filter(f=>f.hash).length;
  countEl.textContent = files.length===0 ? 'Nenhum arquivo na custódia' : `${files.length} na bandeja • ${done} com hash`;
  clearBtn.disabled = files.length===0;
  copyAllBtn.disabled = done===0;
  openAllVtBtn.disabled = done===0;
  checkAllApiBtn.disabled = done===0;
  scanAllLocalBtn.disabled = done===0;
}

function vtBadge(stats){
  if(!stats) return '<span class="vt-badge vt-unknown">—</span>';
  const mal = stats.malicious||0, susp = stats.suspicious||0, und = stats.undetected||0, harm = stats.harmless||0, timeout = stats.timeout||0, fail = stats['failure']||0, conf = stats['confirmed-timeout']||0, unsup = stats['type-unsupported']||0;
  const total = mal+susp+und+harm+timeout+fail+conf+unsup;
  const clean = und+harm;
  const detected = mal+susp;
  const passed = clean;
  let cls='vt-clean', label=`✓ ${passed}/${total} passaram`;
  if(detected>0 && detected<=3) { cls='vt-suspicious'; label=`⚠ ${detected}/${total} detectaram`; }
  else if(detected>3) { cls='vt-malicious'; label=`⛔ ${detected}/${total} maliciosos`; }
  else if(total>0) { label=`✓ ${clean}/${total} limpos`; }
  const t_o = timeout+fail+conf;
  return `<span class="vt-badge ${cls}">${label}</span><div class="vt-detail">${clean} limpos • ${mal} mal • ${susp} sus • ${t_o} timeout • ${unsup} não suportado</div>`;
}
function vtLogsHtml(stats, results){
  if(!stats) return '';
  const mal = stats.malicious||0, susp = stats.suspicious||0;
  const und = stats.undetected||0, harm = stats.harmless||0;
  const timeout = stats.timeout||0, fail = stats['failure']||0, conf = stats['confirmed-timeout']||0, unsup = stats['type-unsupported']||0;
  const total = mal+susp+und+harm+timeout+fail+conf+unsup;
  const clean = und+harm;
  let html = `<div style="margin-top:8px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-family:Geist Mono,monospace;font-size:10px;line-height:1.6">`;
  html += `<div style="color:var(--text-2);margin-bottom:6px">Logs VT: <b style="color:var(--text)">${clean}/${total} passaram</b> • ${mal} maliciosos • ${susp} suspeitos • ${timeout+fail+conf} timeout • ${unsup} não suportado</div>`;
  if(results && typeof results==='object'){
    const entries = Object.entries(results);
    const malList = entries.filter(([,v])=>v.category==='malicious').slice(0,12);
    const suspList = entries.filter(([,v])=>v.category==='suspicious').slice(0,6);
    const timeoutList = entries.filter(([,v])=>v.category==='timeout' || v.category==='confirmed-timeout').slice(0,8);
    const unsupList = entries.filter(([,v])=>v.category==='type-unsupported' || (v.result||'').toLowerCase().includes('unable to process')).slice(0,10);
    const failList = entries.filter(([,v])=>v.category==='failure').slice(0,6);
    if(malList.length){
      html += `<div style="color:var(--red);margin-top:6px">Maliciosos (${malList.length}${entries.filter(([,v])=>v.category==='malicious').length>12?' de '+entries.filter(([,v])=>v.category==='malicious').length:''}):</div>`;
      html += malList.map(([k,v])=>`<div>• ${escapeHtml(k)} → ${escapeHtml(v.result||v.category)}</div>`).join('');
    }
    if(suspList.length){
      html += `<div style="color:var(--yellow);margin-top:6px">Suspeitos:</div>`;
      html += suspList.map(([k,v])=>`<div>• ${escapeHtml(k)} → ${escapeHtml(v.result||'')}</div>`).join('');
    }
    if(timeoutList.length){
      html += `<div style="color:var(--text-2);margin-top:6px">Timeout (${timeoutList.length}):</div>`;
      html += timeoutList.map(([k,v])=>`<div>• ${escapeHtml(k)} → ${escapeHtml(v.result||'Timeout')}</div>`).join('');
    }
    if(unsupList.length){
      html += `<div style="color:var(--muted);margin-top:6px">Não suportado / Unable to process (${unsupList.length}):</div>`;
      html += unsupList.map(([k,v])=>`<div>• ${escapeHtml(k)} → ${escapeHtml(v.result||'Unable to process file type')}</div>`).join('');
    }
    if(failList.length){
      html += `<div style="color:var(--muted);margin-top:6px">Failure:</div>`;
      html += failList.map(([k,v])=>`<div>• ${escapeHtml(k)} → ${escapeHtml(v.result||'failure')}</div>`).join('');
    }
    if(!malList.length && !suspList.length && !timeoutList.length && !unsupList.length){
      html += `<div style="color:var(--muted)">Nenhum engine marcou como malicioso — ${clean} passaram limpos.</div>`;
    }
    const shown = malList.length + suspList.length + timeoutList.length + unsupList.length + failList.length;
    if(entries.length>shown){
      const remaining = entries.slice(shown, shown+20);
      html += `<div style="margin-top:6px;opacity:0.6">+ ${entries.length-shown} engines omitidos • <a href="#" onclick="event.preventDefault(); this.nextElementSibling.style.display='block'; this.style.display='none'" style="color:var(--accent)">ver todos</a><div style="display:none">${entries.slice(shown).map(([k,v])=>`<div>${escapeHtml(k)}: ${escapeHtml(v.category)} ${escapeHtml(v.result||'')}</div>`).join('')}</div></div>`;
    }
  }
  html += `</div>`;
  return html;
}

function showToast(msg){
  let t=document.getElementById('toast');
  if(!t){ t=document.createElement('div'); t.id='toast'; t.style.cssText='position:fixed;bottom:20px;left:50%;transform:translateX(-50%);background:var(--surface);color:var(--text);border:1px solid var(--border);padding:12px 16px;border-radius:999px;font-family:Geist Mono,monospace;font-size:12px;max-width:520px;text-align:center;z-index:9999;box-shadow:0 16px 32px rgba(0,0,0,0.4)'; document.body.appendChild(t); }
  t.innerHTML=msg; t.style.display='block';
  clearTimeout(t._timer); t._timer=setTimeout(()=>t.style.display='none', 4000);
}

function formatMs(ms){
  if(ms==null) return '';
  if(ms<1000) return ms+'ms';
  const s=(ms/1000).toFixed(1);
  return s+'s';
}
function localBadge(local){
  if(!local) return '<span class="vt-badge vt-unknown">—</span>';
  if(local && local.skipped) return '<span class="vt-badge vt-unknown" style="opacity:0.7">— VT usado</span><div class="vt-detail">Scan local não necessário (VT OK)</div>';
  if(local.loading){
    const elapsed = local.startTime ? ((Date.now()-local.startTime)/1000).toFixed(1) : '0.0';
    const pct = local.uploadProgress!=null ? Math.round(local.uploadProgress*100) : 30;
    const phase = pct<70 ? 'enviando' : (pct<95 ? 'scan' : 'fim');
    return `<span class="status hashing local-status">⏳ ${phase} ${elapsed}s</span><div class="progress-bar"><div class="progress-fill local-progress" style="width:${pct}%"></div></div>`;
  }
  if(local.error) return `<span class="status">⚠️ ${escapeHtml(local.error)}</span><div class="vt-detail"><a href="#" onclick="scanLocal('${local.id||''}'); return false;" style="color:var(--accent);text-decoration:underline">tentar novamente</a></div>`;
  if(local.infected) {
    const t = local.total_time_ms ? ` • ${formatMs(local.total_time_ms)}` : (local.scan_time_ms?` • ${formatMs(local.scan_time_ms)}`:'');
    return `<span class="vt-badge vt-malicious">⛔ Infectado${t}</span><div class="vt-detail" style="color:var(--red)">${escapeHtml(local.summary||local.signatures||'Detectado')}</div><div class="vt-detail">${local.clamav?.time_ms?'ClamAV '+formatMs(local.clamav.time_ms):''} ${local.yara?.time_ms?' + YARA '+formatMs(local.yara.time_ms):''}</div>`;
  }
  if(local.available === false) return `<span class="vt-badge vt-unknown">⚠️ Engine OFF</span><div class="vt-detail">${escapeHtml(local.error||'ClamAV/YARA não instalado')}</div>`;
  const t = local.total_time_ms ? ` • ${formatMs(local.total_time_ms)}` : (local.scan_time_ms?` • ${formatMs(local.scan_time_ms)}`:'');
  return `<span class="vt-badge vt-clean">✓ Limpo${t}</span><div class="vt-detail">ClamAV ${local.clamav?.time_ms?formatMs(local.clamav.time_ms):''} + YARA ${local.yara?.time_ms?formatMs(local.yara.time_ms):''}`.trim()+'</div>';
}

function render(){
  if(isSelecting){ pendingRender=true; updateToolbar(); return; }
  if(files.length===0){
    tbody.innerHTML='<tr><td colspan="5"><div class="empty-state"><span>⬢</span><b>Bandeja vazia</b>Solte arquivos acima. Hash local + VT + ClamAV/YARA. Fechar limpa tudo.<br><span style="font-family:Geist Mono,monospace;font-size:11px;color:var(--muted);margin-top:8px;display:inline-block;border:1px dashed var(--border);padding:4px 8px;border-radius:999px">01 Hash → 02 Verify → 03 Scan</span></div></td></tr>';
    updateToolbar(); return;
  }
  tbody.innerHTML = files.map(f=>`
    <tr data-fid="${f.id}">
      <td>
        <span class="file-name" title="${escapeHtml(f.name)}">${escapeHtml(f.name)}</span>
        <div class="file-size">${formatBytes(f.size)}${f.size>650*1024*1024 ? '<br><span style="color:var(--red);font-size:10px;font-family:Geist Mono,monospace">›650MB — VT N/A</span>' : ''}</div>
      </td>
      <td>
        ${f.status==='hashing' ? `<div class="status hashing hashing-status">⏳ ${f.progress ? Math.round(f.progress*100)+'%' : 'iniciando…'} ${f.size>50*1024*1024 ? '('+formatBytes(f.hashed||0)+' / '+formatBytes(f.size)+')' : ''}</div><div class="progress-bar"><div class="progress-fill" style="width:${Math.round((f.progress||0)*100)}%"></div></div>` : ''}
        ${f.status==='error' ? `<span class="status">❌ ${escapeHtml(f.error||'erro')}</span>` : ''}
        ${f.hash ? `<code class="hash" style="user-select:text;-webkit-user-select:text;cursor:text">${f.hash}</code>` : ''}
      </td>
      <td>
        ${f.vt?.loading ? '<span class="status hashing">⏳ consultando VT…</span>' : ''}
        ${f.vt?.error ? `<span class="status">❌ ${escapeHtml(f.vt.error)}</span>` : ''}
        ${!f.vt?.loading && !f.vt?.error && f.vt?.stats ? vtBadge(f.vt.stats) : (!f.vt?.loading && !f.vt?.error ? vtBadge(null) : '')}
        ${f.vt?.stats ? vtLogsHtml(f.vt.stats, f.vt.results) : ''}
        ${f.vt?.stats ? `<div class="vt-detail"><a href="https://www.virustotal.com/gui/file/${f.hash}" target="_blank" rel="noopener noreferrer" style="color:var(--accent);text-decoration:underline">abrir no VT ↗</a>${f.vt.date ? ` • ${new Date(f.vt.date*1000).toLocaleDateString('pt-BR')}` : ''}</div>` : ''}
        ${!f.vt?.stats && !f.vt?.loading && !f.vt?.error && f.size>650*1024*1024 ? '<div class="vt-detail" style="color:var(--red)">›650MB — VT não aceita</div>' : ''}
      </td>
      <td>
        ${localBadge(f.local)}
        ${f.local?.clamav?.signature ? `<div class="vt-detail">ClamAV: ${escapeHtml(f.local.clamav.signature)}</div>` : ''}
        ${f.local?.yara?.signature ? `<div class="vt-detail">YARA: ${escapeHtml(f.local.yara.signature)}</div>` : ''}
      </td>
      <td>
        <div class="actions-cell">
          ${f.hash ? `<button class="btn-sm" onclick="copyHash('${f.hash}', this)">📋 Copiar</button>` : ''}
          ${f.size<=650*1024*1024 && f.hash ? `<button class="btn-sm" onclick="openVTIncognito('${f.hash}')">VT anonimo</button>` : ''}
          ${f.hash ? `<button class="btn-sm" onclick="checkOne('${f.id}')">API</button>` : ''}
          ${f.hash ? `<button class="btn-sm" style="background:var(--accent);color:var(--accent-ink);border-color:var(--accent)" onclick="scanLocal('${f.id}')">Scan Local</button>` : ''}
        </div>
      </td>
    </tr>
  `).join('');
  updateToolbar();
}

async function computeSha256(file, onProgress){
  if(file.size < 50 * 1024 * 1024){
    try{
      const buf = await file.arrayBuffer();
      const hashBuf = await crypto.subtle.digest('SHA-256', buf);
      if(onProgress) onProgress(1, file.size);
      return Array.from(new Uint8Array(hashBuf)).map(b=>b.toString(16).padStart(2,'0')).join('');
    }catch(e){ console.warn("Web Crypto falhou, streaming:", e); }
  }
  const chunkSize = 4 * 1024 * 1024;
  const chunks = Math.ceil(file.size / chunkSize);
  const lib = (typeof window !== 'undefined' && window.sha256) ? window.sha256 : (typeof sha256 !== 'undefined' ? sha256 : null);
  const hasher = (lib && lib.create) ? lib.create() : null;
  if(!hasher) throw new Error("lib sha256 não carregada");
  for(let i=0;i<chunks;i++){
    const start = i * chunkSize;
    const end = Math.min(start + chunkSize, file.size);
    const slice = file.slice(start, end);
    const buf = await slice.arrayBuffer();
    hasher.update(new Uint8Array(buf));
    if(onProgress) onProgress((i+1)/chunks, end);
    if(i % 4 === 0) await new Promise(r=>setTimeout(r, 0));
  }
  return hasher.hex();
}

async function addFiles(list){
  const news = Array.from(list).map(file=>({ id:Math.random().toString(36).slice(2)+Date.now(), name:file.name, size:file.size, fileObj:file, rawFile: file, hash:null, status:'hashing', progress:0, hashed:0, vt:null, local:null }));
  files.push(...news);
  render();
  for(const e of news){
    try{
      e.hash = await computeSha256(e.fileObj, (p, hashed)=>{
        e.progress = p; e.hashed = hashed;
        if(isSelecting){
          updateRowProgress(e.id);
        } else if(!e._lastRender || Date.now() - e._lastRender > 200){
          e._lastRender = Date.now();
          // se estiver selecionando, não recria tabela
          if(isSelecting) updateRowProgress(e.id); else render();
        } else {
          // atualização leve sem recriar
          updateRowProgress(e.id);
        }
      });
      e.status='done'; e.progress=1;
    }catch(err){ console.error("hash erro", e.name, err); e.status='error'; e.error = err.message || 'falha'; }
    delete e.fileObj;
    if(isSelecting){ pendingRender=true; } else { render(); }
    if(e.status==='done'){
      if(e.size <= 650*1024*1024){
        // VT primeiro (via API se tem key, senão Playwright scrape). Só vai para ClamAV se VT falhar.
        const key = apiKeyInput.value.trim();
        let vtOk = false;
        if(key){
          await checkOne(e.id);
          const cur = files.find(x=>x.id===e.id);
          vtOk = !!(cur && cur.vt && cur.vt.stats);
        } else {
          await scrapeVTOne(e.id);
          const cur = files.find(x=>x.id===e.id);
          vtOk = !!(cur && cur.vt && cur.vt.stats);
        }
        if(!vtOk){
          await scanLocal(e.id);
        } else {
          // VT ok, marca local como skipped (não gastou ClamAV)
          const cur = files.find(x=>x.id===e.id);
          if(cur && !cur.local){
            cur.local = { skipped:true, viaVT:true, id:e.id };
            if(isSelecting) pendingRender=true; else render();
          }
        }
      } else {
        // >650MB VT impossível, direto ClamAV
        await scanLocal(e.id);
      }
    }
  }
}

async function scanLocal(id){
  const f = files.find(x=>x.id===id);
  if(!f || !f.rawFile) {
    const ff = files.find(x=>x.id===id);
    if(!ff) return;
    if(!ff.rawFile){ showToast(`❌ Arquivo ${ff.name} precisa ser re-selecionado`); return; }
  }
  const file = files.find(x=>x.id===id).rawFile;
  if(!file) return;
  const entry = files.find(x=>x.id===id);
  entry.local = { loading: true, uploadProgress: 0, startTime: Date.now(), size: file.size, id: id };
  if(isSelecting) pendingRender=true; else render();
  const timer = setInterval(()=>{
    if(!entry.local?.loading){ clearInterval(timer); return; }
    if(isSelecting) updateRowProgress(id);
    else render();
  }, 200);
  try{
    const xhr = new XMLHttpRequest();
    const prom = new Promise((resolve, reject)=>{
      xhr.open('POST', 'http://localhost:8765/scan');
      xhr.setRequestHeader('X-Filename', encodeURIComponent(file.name));
      xhr.onload = ()=>{
        if(xhr.status>=200 && xhr.status<300){
          try{ resolve(JSON.parse(xhr.responseText)); } catch(e){ reject(e); }
        } else { reject(new Error(xhr.responseText || `HTTP ${xhr.status}`)); }
      };
      xhr.onerror = ()=> reject(new Error('Falha conexao com server local (rode FileHasher.bat)'));
      xhr.upload.onprogress = (e)=>{
        if(e.lengthComputable){
          entry.local.uploadProgress = e.loaded / e.total * 0.7;
          if(isSelecting) updateRowProgress(id); else render();
        }
      };
      xhr.upload.onload = ()=>{
        entry.local.uploadProgress = 0.85;
        if(isSelecting) updateRowProgress(id); else render();
      };
      xhr.send(file);
    });
    const result = await prom;
    clearInterval(timer);
    entry.local = {
      loading: false, infected: result.infected, signatures: result.signatures?.join(', '),
      summary: result.summary, clamav: result.clamav, yara: result.yara, available: true, id: id,
      total_time_ms: result.total_time_ms, scan_time_ms: result.scan_time_ms, upload_time_ms: result.upload_time_ms
    };
    if(result.error) entry.local.error = result.error;
  }catch(err){
    clearInterval(timer); console.error("scanLocal erro", err);
    let msg = err.message || 'erro';
    if(msg.includes('Failed to fetch') || msg.includes('conexao')){ msg = 'Server OFF — rode FileHasher.bat'; }
    entry.local = { loading: false, error: msg, id: id };
  }
  if(isSelecting) pendingRender=true; else render();
}

async function scanAllLocal(){
  for(const f of files.filter(x=>x.hash && x.rawFile)){
    await scanLocal(f.id); await new Promise(r=>setTimeout(r, 300));
  }
}

function openVT(hash){ window.open(`https://www.virustotal.com/gui/file/${hash}`, '_blank', 'noopener,noreferrer'); }
async function tryOpenIncognitoViaServer(hash){
  try{
    const controller = new AbortController();
    const t = setTimeout(()=>controller.abort(), 1500);
    const res = await fetch(`http://localhost:8765/open?hash=${hash}`, { method: 'GET', signal: controller.signal });
    clearTimeout(t);
    if(res.ok){ const j = await res.json(); showToast(`✅ Anônimo!<br><span style="opacity:0.7">${j.status}</span>`); return true; }
  }catch(e){}
  return false;
}
function openVTIncognito(hash){
  const url = `https://www.virustotal.com/gui/file/${hash}`;
  // Abre fallbackWin SINCRONAMENTE para preservar gesto (popup blocker)
  // Se server responder OK, fechamos o fallback e usamos server (Python --incognito)
  let fallbackWin = null;
  try{ fallbackWin = window.open('about:blank', '_blank'); }catch(e){ fallbackWin=null; }
  // Tenta server
  fetch(`http://localhost:8765/open?hash=${hash}`, {method:'GET'}).then(async res=>{
    if(res.ok){
      const j=await res.json().catch(()=>({}));
      if(fallbackWin && !fallbackWin.closed) try{ fallbackWin.close(); }catch(e){}
      showToast(`✅ Anônimo via server!<br><span style="opacity:0.7">${j.status||'ok'}</span>`);
      navigator.clipboard.writeText(url).catch(()=>{});
    } else {
      if(fallbackWin && !fallbackWin.closed){ fallbackWin.location.href = url; }
      else { window.open(url, '_blank', 'noopener,noreferrer'); }
      navigator.clipboard.writeText(url).catch(()=>{});
      showToast(`🔗 Aberto VT (fallback)`);
    }
  }).catch(()=>{
    if(fallbackWin && !fallbackWin.closed){ fallbackWin.location.href = url; }
    else {
      const win2 = window.open(url, '_blank', 'noopener,noreferrer');
      if(!win2) showToast('⚠️ Popup bloqueado! Permita popups ou copie o hash.');
    }
    navigator.clipboard.writeText(url).catch(()=>{});
  });
  // Se fetch demorar >1.2s e fallbackWin ainda em about:blank, assume server OFF e navega
  setTimeout(()=>{
    try{
      if(fallbackWin && !fallbackWin.closed && fallbackWin.location.href==='about:blank'){
        // ainda não navegou e server não respondeu rápido, deixa para fetch resolver
        // mas se fetch já falhou, fallback já navegou
      }
    }catch(e){}
  }, 1200);
}
function openAllVTIncognito(){
  // Para múltiplos, usa server sequencial (não precisa gesto) — abre via Python, não via window
  fetch(`http://localhost:8765/ping`).then(r=>{
    if(r.ok){
      (async()=>{
        for(const f of files.filter(x=>x.hash)){
          try{ await fetch(`http://localhost:8765/open?hash=${f.hash}`); }catch(e){}
          await new Promise(rr=>setTimeout(rr, 400));
        }
        showToast(`✅ ${files.filter(f=>f.hash).length} links em anônimo via server!`);
      })();
    } else { throw new Error(); }
  }).catch(()=>{
    // Fallback: precisa gesto, mas para múltiplos o browser bloqueia de qualquer jeito — copia links
    const hashes = files.filter(f=>f.hash).map(f=>`https://www.virustotal.com/gui/file/${f.hash}`).join('\n');
    navigator.clipboard.writeText(hashes).catch(()=>{});
    // Tenta abrir um por um com delay para não ser bloqueado
    let i=0;
    const openNext = ()=>{
      if(i>=files.length) return;
      const f=files.filter(x=>x.hash)[i++];
      if(f) window.open(`https://www.virustotal.com/gui/file/${f.hash}`, '_blank', 'noopener,noreferrer');
      if(i<files.length) setTimeout(openNext, 300);
    };
    openNext();
    showToast(`🔗 Server OFF — links copiados! Cole no VT.`);
  });
}
async function fetchVT(hash, apiKey){
  const res = await fetch(`https://www.virustotal.com/api/v3/files/${hash}`, { headers: { 'x-apikey': apiKey } });
  if(res.status===404){ throw new Error('Não encontrado no VT (nunca enviado)'); }
  if(res.status===429) throw new Error('Rate limit (4/min)');
  if(res.status===401) throw new Error('API key inválida');
  if(!res.ok) throw new Error(`VT erro ${res.status}`);
  const data = await res.json();
  const a = data.data.attributes;
  return { stats: a.last_analysis_stats, results: a.last_analysis_results, date: a.last_analysis_date };
}
async function scrapeVTOne(id){
  const f = files.find(x=>x.id===id);
  if(!f?.hash) return;
  if(f.size>650*1024*1024) return;
  f.vt = { loading:true, via:'playwright' }; render();
  try{
    const res = await fetch(`http://localhost:8765/vt-scrape?hash=${f.hash}`);
    const data = await res.json();
    if(!res.ok || data.error && !data.stats) throw new Error(data.error || `HTTP ${res.status}`);
    if(data.stats){
      f.vt = { loading:false, stats: data.stats, results: data.results, date: Date.now()/1000, via:'playwright', time_ms: data.time_ms };
    } else {
      throw new Error(data.error||'Sem stats');
    }
  }catch(e){
    const msg = e.message.includes('playwright') ? e.message : `Scrape falhou: ${e.message}. Use API key em Config para confiável.`;
    f.vt = { loading:false, error: msg };
  }
  render();
}
async function checkOne(id){
  const f = files.find(x=>x.id===id);
  if(!f?.hash) return;
  const key = apiKeyInput.value.trim();
  if(!key){ showToast('Cole API key em Config → VirusTotal'); document.querySelector('[data-tab="config"]').click(); return; }
  f.vt = { loading:true }; render();
  try{ const r = await fetchVT(f.hash, key); f.vt = { loading:false, stats: r.stats, results: r.results, date: r.date }; }catch(e){ f.vt = { loading:false, error: e.message }; }
  render();
}
async function checkAllViaApi(){
  const key = apiKeyInput.value.trim();
  if(!key){ showToast('Cole API key em Config'); document.querySelector('[data-tab="config"]').click(); return; }
  for(const f of files.filter(x=>x.hash)){
    f.vt = { loading:true }; render();
    try{ const r = await fetchVT(f.hash, key); f.vt = { loading:false, stats: r.stats, results: r.results, date: r.date }; }catch(e){
      f.vt = { loading:false, error: e.message };
      if(e.message.includes('Rate limit')){ render(); await new Promise(r=>setTimeout(r, 16000)); continue; }
    }
    render(); await new Promise(r=>setTimeout(r, 16000));
  }
}

// Tabs
document.querySelectorAll('.nav button').forEach(btn=>{
  btn.addEventListener('click', ()=>{
    document.querySelectorAll('.nav button').forEach(b=>{b.classList.remove('active'); b.setAttribute('aria-selected','false')});
    btn.classList.add('active'); btn.setAttribute('aria-selected','true');
    document.querySelectorAll('.view').forEach(v=>v.classList.remove('active'));
    document.getElementById('view-'+btn.dataset.tab).classList.add('active');
  });
});
// Help modal
const helpModal = document.getElementById('helpModal');
document.getElementById('helpBtn').addEventListener('click', ()=>{ helpModal.classList.add('open'); helpModal.setAttribute('aria-hidden','false'); });
document.getElementById('closeHelp').addEventListener('click', ()=>{ helpModal.classList.remove('open'); helpModal.setAttribute('aria-hidden','true'); });
helpModal.addEventListener('click', (e)=>{ if(e.target===helpModal){ helpModal.classList.remove('open'); }});
document.addEventListener('keydown', (e)=>{ if(e.key==='Escape' && helpModal.classList.contains('open')) helpModal.classList.remove('open'); });

// Events
pickBtn.addEventListener('click', ()=>fileInput.click());
dropZone.addEventListener('click', (e)=>{
  if(e.target===dropZone || e.target.closest('.drop-icon') || e.target.closest('.title') || e.target.closest('.subtitle')) fileInput.click();
});
dropZone.addEventListener('keydown', (e)=>{ if(e.key==='Enter'||e.key===' ') { e.preventDefault(); fileInput.click(); }});
fileInput.addEventListener('change', ()=>{ if(fileInput.files.length){ addFiles(fileInput.files); fileInput.value=''; }});
['dragenter','dragover'].forEach(ev=>dropZone.addEventListener(ev, e=>{ e.preventDefault(); dropZone.classList.add('dragover'); }));
['dragleave','drop'].forEach(ev=>dropZone.addEventListener(ev, e=>{ e.preventDefault(); dropZone.classList.remove('dragover'); }));
dropZone.addEventListener('drop', e=>{ if(e.dataTransfer.files.length) addFiles(e.dataTransfer.files); });
clearBtn.addEventListener('click', ()=>{ files=[]; render(); });
copyAllBtn.addEventListener('click', async ()=>{
  const text = files.filter(f=>f.hash).map(f=>`${f.name}  ${f.hash}`).join('\n');
  await navigator.clipboard.writeText(text);
  const o=copyAllBtn.textContent; copyAllBtn.textContent='✓ Copiado!'; setTimeout(()=>copyAllBtn.textContent=o,1500);
});
openAllVtBtn.addEventListener('click', openAllVTIncognito);
checkAllApiBtn.addEventListener('click', checkAllViaApi);
scanAllLocalBtn.addEventListener('click', scanAllLocal);
window.scanLocal = scanLocal;
window.scanAllLocal = scanAllLocal;
window.copyHash = async (hash, btn)=>{
  await navigator.clipboard.writeText(hash);
  btn.textContent='✓ Copiado'; btn.classList.add('copied');
  setTimeout(()=>{ btn.textContent='📋 Copiar'; btn.classList.remove('copied'); },1500);
};
window.openVT = openVT;
window.openVTIncognito = openVTIncognito;
window.checkOne = checkOne;
async function checkServerStatus(){
  const dot = document.getElementById('serverDot');
  const txt = document.getElementById('serverStatusText');
  if(!txt) return;
  try{
    const res = await fetch(`http://localhost:8765/ping`, { method: 'GET' });
    if(res.ok){
      txt.textContent = 'Servidor ON — VT anonimo e Scan Local ativos';
      dot.classList.add('on'); dot.classList.remove('off');
    } else { throw new Error(); }
  }catch(e){
    txt.textContent = 'Servidor OFF — rode FileHasher.bat';
    dot.classList.add('off'); dot.classList.remove('on');
  }
}
async function checkLocalHealth(){
  if(!localHealthEl) return;
  try{
    const res = await fetch(`http://localhost:8765/health/scan`);
    if(!res.ok) throw new Error();
    const j = await res.json();
    const clam = j.clamav_available ? '✅ ClamAV OK' : '❌ ClamAV OFF';
    const yara = j.yara_available ? (j.yara_rules_available ? '✅ YARA OK' : '⚠️ YARA sem regras') : '❌ YARA OFF';
    localHealthEl.textContent = `${clam} • ${yara} — Scan Local sempre ativo`;
    localHealthEl.style.color = (j.clamav_available || j.yara_available) ? 'var(--accent)' : 'var(--red)';
    if(localHealthText){
      const db = j.clamav_db ? `DB: ${j.clamav_db}` : '';
      localHealthText.textContent = `${clam} • ${yara}`;
      localHealthDetail.textContent = db;
      localDot.className = 'status-dot ' + ((j.clamav_available||j.yara_available)?'on':'off');
    }
  }catch(e){
    localHealthEl.textContent = '⚠️ Scan Local OFF — rode FileHasher.bat';
    localHealthEl.style.color = 'var(--red)';
    if(localHealthText){ localHealthText.textContent='Servidor OFF'; localDot.className='status-dot off'; }
  }
}
checkServerStatus(); checkLocalHealth();
setInterval(checkServerStatus, 5000);
setInterval(checkLocalHealth, 7000);
window.addEventListener('beforeunload', ()=>{ files=[]; if(apiKeyInput) apiKeyInput.value=''; });
window.addEventListener('paste', e=>{ const fs=e.clipboardData?.files; if(fs?.length) addFiles(fs); });