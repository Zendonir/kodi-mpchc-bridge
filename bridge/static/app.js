// ── i18n ─────────────────────────────────────────────────────────────────────
const _LANG = (navigator.language || 'en').slice(0,2).toLowerCase();
const _TR = {
  en:{
    status_connecting:'Connecting…',status_connected:'● Connected',
    status_reconnecting:'○ Disconnected – reconnecting…',
    card_controls:'Controls',card_playback:'Playback',card_details:'Details',
    card_video:'Video Info',card_tracks:'Tracks',card_season:'Season',
    card_logs:'Bridge Log',card_settings:'Settings',
    btn_skip_back:'⏪ −1 min',btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',btn_seek_fwd:'+10s',
    btn_seek_minus:'⏪ s',btn_seek_plus:'s ⏩',
    btn_back:'← Back',btn_home:'⌂ Home',btn_menu:'☰ Menu',
    btn_info:'ℹ Info',btn_watched:'☆ Unwatched',btn_watched_on:'★ Watched',
    btn_fullscreen:'⛶ Fullscreen',btn_restart_pc:'⏻ Restart PC',
    confirm_restart:'Schedule a system restart in 10 seconds?',
    btn_kiosk_kodi:'Kodi',btn_kiosk_windows:'Windows',btn_kiosk_restart:'Restart Kodi',
    btn_prev_ep:'⏮ Prev',btn_next_ep:'Next ⏭',
    btn_logs:'\U0001f4cb Log',btn_log_refresh:'↻',btn_settings:'⚙ Settings',
    nav_up:'Up',nav_down:'Down',nav_left:'Left',nav_right:'Right',nav_ok:'OK (Enter)',
    kbd_hint:'Keyboard: <kbd>↑↓←→</kbd> navigate &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Back &nbsp;<kbd>Space</kbd> Play/Pause',
    lbl_active_player:'Player',lbl_state:'Status',lbl_title:'Title',
    lbl_artist:'Artist',lbl_album:'Album',lbl_media_type:'Type',
    lbl_position:'Position',lbl_duration:'Duration',lbl_volume:'Volume',
    lbl_muted:'Muted',lbl_shuffle:'Shuffle',lbl_repeat:'Repeat',
    lbl_year:'Year',lbl_tv_show:'Show',lbl_season:'Season',lbl_episode:'Episode',
    lbl_rating:'Rating',
    lbl_video_width:'Width',lbl_video_height:'Height',lbl_video_fps:'Frame rate',
    lbl_hdr:'HDR',lbl_video_codec:'Codec',lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio',lbl_current_subtitle:'Subtitle',lbl_current_chapter:'Chapter',
    lbl_art_movie:'Movie',lbl_art_episode:'TV Series',lbl_art_music:'Music',
    opt_art_poster:'Poster',opt_art_fanart:'Fanart / Backdrop',opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Series poster',opt_art_seasonposter:'Season poster',
    lbl_kodi_exe:'Kodi path:',lbl_boot_target:'Boot target',
    opt_boot_kodi:'Kodi — hide Explorer on startup',
    opt_boot_windows:'Windows — normal desktop',
    val_yes:'Yes',val_no:'No',val_of:'of',
  },
  de:{
    status_connecting:'Verbinde…',status_connected:'● Verbunden',
    status_reconnecting:'○ Getrennt – verbinde erneut…',
    card_controls:'Steuerung',card_playback:'Wiedergabe',card_details:'Details',
    card_video:'Video-Info',card_tracks:'Spuren',card_season:'Staffel',
    card_logs:'Bridge Log',card_settings:'Einstellungen',
    btn_skip_back:'⏪ −1 min',btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',btn_seek_fwd:'+10s',
    btn_seek_minus:'⏪ s',btn_seek_plus:'s ⏩',
    btn_back:'← Zurück',btn_home:'⌂ Home',btn_menu:'☰ Menü',
    btn_info:'ℹ Info',btn_watched:'☆ Ungesehen',btn_watched_on:'★ Gesehen',
    btn_fullscreen:'⛶ Vollbild',btn_restart_pc:'⏻ PC neu starten',
    confirm_restart:'PC in 10 Sekunden neu starten?',
    btn_kiosk_kodi:'Kodi',btn_kiosk_windows:'Kodi Windows',btn_kiosk_restart:'Kodi neustarten',
    btn_prev_ep:'⏮ Zurück',btn_next_ep:'Weiter ⏭',
    btn_logs:'\U0001f4cb Log',btn_log_refresh:'↻',btn_settings:'⚙ Einstellungen',
    nav_up:'Hoch',nav_down:'Runter',nav_left:'Links',nav_right:'Rechts',nav_ok:'OK (Enter)',
    kbd_hint:'Tastatur: <kbd>↑↓←→</kbd> navigieren &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Zurück &nbsp;<kbd>Leertaste</kbd> Play/Pause',
    lbl_active_player:'Player',lbl_state:'Status',lbl_title:'Titel',
    lbl_artist:'Interpret',lbl_album:'Album',lbl_media_type:'Typ',
    lbl_position:'Position',lbl_duration:'Dauer',lbl_volume:'Lautstärke',
    lbl_muted:'Stumm',lbl_shuffle:'Shuffle',lbl_repeat:'Wiederholen',
    lbl_year:'Jahr',lbl_tv_show:'Serie',lbl_season:'Staffel',lbl_episode:'Folge',
    lbl_rating:'Bewertung',
    lbl_video_width:'Breite',lbl_video_height:'Höhe',lbl_video_fps:'Framerate',
    lbl_hdr:'HDR',lbl_video_codec:'Codec',lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio-Spur',lbl_current_subtitle:'Untertitel',lbl_current_chapter:'Kapitel',
    lbl_art_movie:'Film',lbl_art_episode:'Serien',lbl_art_music:'Musik',
    opt_art_poster:'Poster',opt_art_fanart:'Fanart / Hintergrund',opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Seriencover',opt_art_seasonposter:'Staffelcover',
    lbl_kodi_exe:'Kodi-Pfad:',lbl_boot_target:'Boot-Ziel',
    opt_boot_kodi:'Kodi — Explorer beim Start verstecken',
    opt_boot_windows:'Windows — normaler Desktop',
    val_yes:'Ja',val_no:'Nein',val_of:'von',
  },
  fr:{
    status_connecting:'Connexion…',status_connected:'● Connecté',
    status_reconnecting:'○ Déconnecté – reconnexion…',
    card_controls:'Contrôles',card_playback:'Lecture',card_details:'Détails',
    card_video:'Infos vidéo',card_tracks:'Pistes',card_season:'Saison',
    card_logs:'Bridge Log',card_settings:'Paramètres',
    btn_back:'← Retour',btn_home:'⌂ Accueil',btn_menu:'☰ Menu',
    btn_info:'ℹ Infos',btn_watched:'☆ Non vu',btn_watched_on:'★ Vu',
    btn_fullscreen:'⛶ Plein écran',btn_restart_pc:'⏻ Redémarrer',
    confirm_restart:'Redémarrer le système dans 10 secondes ?',
    btn_kiosk_kodi:'Kodi',btn_kiosk_windows:'Windows',btn_kiosk_restart:'Relancer Kodi',
    btn_prev_ep:'⏮ Préc',btn_next_ep:'Suiv ⏭',
    btn_logs:'\U0001f4cb Journal',btn_log_refresh:'↻',btn_settings:'⚙ Paramètres',
    lbl_year:'Année',lbl_tv_show:'Série',lbl_season:'Saison',lbl_episode:'Épisode',
    lbl_volume:'Volume',lbl_muted:'Muet',lbl_shuffle:'Aléatoire',lbl_repeat:'Répéter',
    val_yes:'Oui',val_no:'Non',val_of:'sur',
  },
  es:{
    status_connecting:'Conectando…',status_connected:'● Conectado',
    status_reconnecting:'○ Desconectado – reconectando…',
    card_controls:'Controles',card_playback:'Reproducción',card_details:'Detalles',
    card_video:'Info de vídeo',card_tracks:'Pistas',card_season:'Temporada',
    card_logs:'Bridge Log',card_settings:'Ajustes',
    btn_back:'← Volver',btn_home:'⌂ Inicio',btn_menu:'☰ Menú',
    btn_info:'ℹ Info',btn_watched:'☆ No visto',btn_watched_on:'★ Visto',
    btn_fullscreen:'⛶ Pantalla completa',btn_restart_pc:'⏻ Reiniciar',
    confirm_restart:'¿Reiniciar el sistema en 10 segundos?',
    btn_kiosk_kodi:'Kodi',btn_kiosk_windows:'Windows',btn_kiosk_restart:'Reiniciar Kodi',
    btn_prev_ep:'⏮ Anterior',btn_next_ep:'Siguiente ⏭',
    btn_logs:'\U0001f4cb Log',btn_log_refresh:'↻',btn_settings:'⚙ Ajustes',
    lbl_year:'Año',lbl_tv_show:'Serie',lbl_season:'Temporada',lbl_episode:'Episodio',
    lbl_volume:'Volumen',lbl_muted:'Silencio',lbl_shuffle:'Aleatorio',lbl_repeat:'Repetir',
    val_yes:'Sí',val_no:'No',val_of:'de',
  },
  it:{
    status_connecting:'Connessione…',status_connected:'● Connesso',
    status_reconnecting:'○ Disconnesso – riconnessione…',
    card_controls:'Controlli',card_playback:'Riproduzione',card_details:'Dettagli',
    card_video:'Info video',card_tracks:'Tracce',card_season:'Stagione',
    card_logs:'Bridge Log',card_settings:'Impostazioni',
    btn_back:'← Indietro',btn_home:'⌂ Home',btn_menu:'☰ Menu',
    btn_info:'ℹ Info',btn_watched:'☆ Non visto',btn_watched_on:'★ Visto',
    btn_fullscreen:'⛶ Schermo intero',btn_restart_pc:'⏻ Riavvia',
    confirm_restart:'Riavviare il sistema tra 10 secondi?',
    btn_kiosk_kodi:'Kodi',btn_kiosk_windows:'Windows',btn_kiosk_restart:'Riavvia Kodi',
    btn_prev_ep:'⏮ Prec',btn_next_ep:'Succ ⏭',
    btn_logs:'\U0001f4cb Log',btn_log_refresh:'↻',btn_settings:'⚙ Impostazioni',
    lbl_year:'Anno',lbl_tv_show:'Serie',lbl_season:'Stagione',lbl_episode:'Episodio',
    lbl_volume:'Volume',lbl_muted:'Muto',lbl_shuffle:'Casuale',lbl_repeat:'Ripeti',
    val_yes:'Sì',val_no:'No',val_of:'di',
  },
};
const _T = Object.assign({}, _TR.en, _TR[_LANG] || {});
function t(k){ return _T[k] || k; }

(function applyI18n(){
  document.querySelectorAll('[data-i18n]').forEach(el => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll('[data-i18n-html]').forEach(el => { el.innerHTML = t(el.dataset.i18nHtml); });
  document.querySelectorAll('[data-i18n-title]').forEach(el => { el.title = t(el.dataset.i18nTitle); });
})();

// ── State ─────────────────────────────────────────────────────────────────────
let state = {};

// ── Helpers ───────────────────────────────────────────────────────────────────
function pad2(n){ return String(n).padStart(2,'0'); }
function fmtTime(s){
  s = Math.round(s || 0);
  return pad2(Math.floor(s/3600)) + ':' + pad2(Math.floor((s%3600)/60)) + ':' + pad2(s%60);
}
function fmtRuntime(s){ if(!s) return ''; return Math.round(s/60) + ' min'; }
function fmtResumeTime(s){
  if(!s) return '';
  s = Math.round(s);
  const h=Math.floor(s/3600), m=Math.floor((s%3600)/60), ss=s%60;
  return h>0 ? h+':'+pad2(m)+':'+pad2(ss) : m+':'+pad2(ss);
}
function fmtVal(k,v){
  if(v===null||v===undefined) return '—';
  if(k==='video_fps')  return v ? v.toFixed(3)+' fps' : '—';
  if(k==='video_bitrate_kbps') return v ? (v/1000).toFixed(1)+' Mbps' : '—';
  if(k==='video_width'||k==='video_height') return v ? v+' px' : '—';
  if(k==='year') return v ? String(v) : '—';
  if(k==='season'){
    if(!v) return '—';
    return state.season_count>0 ? v+' '+t('val_of')+' '+state.season_count : String(v);
  }
  if(k==='episode'){
    if(!v) return '—';
    return state.episode_count>0 ? v+' '+t('val_of')+' '+state.episode_count : String(v);
  }
  if(k==='rating') return v ? v.toFixed(1) : '—';
  if(typeof v==='boolean') return v ? t('val_yes') : t('val_no');
  return v ? String(v) : '—';
}

// ── API helpers ───────────────────────────────────────────────────────────────
function cmd(c, val){
  const body={cmd:c};
  if(val!==undefined) body.value=val;
  fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>{});
}
function seekCustom(sign){
  const s=parseFloat((document.getElementById('seek-secs')||{}).value||'30');
  if(!isNaN(s)&&s>0) cmd('seek_relative', sign*s);
}
function seekByClick(e){
  const rect=e.currentTarget.getBoundingClientRect();
  const pct=(e.clientX-rect.left)/rect.width;
  const dur=state.duration||0;
  if(dur>0) cmd('seek_relative', Math.round(pct*dur - (state.position||0)));
}
function restartConfirm(){ if(confirm(t('confirm_restart'))) cmd('system_restart'); }
function kioskCmd(mode){
  fetch('/api/kiosk/'+mode,{method:'POST'}).catch(()=>{});
  setTimeout(updateKioskStatus,4000);
}
function playEpisode(fp){
  fetch('/api/external_play',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({filepath:fp})}).catch(()=>{});
}
function prevEpisode(){
  const eps=state.season_episodes, idx=state.playlist_index??-1;
  if(eps&&idx>0) playEpisode(eps[idx-1].file);
}
function nextEpisode(){
  const eps=state.season_episodes, idx=state.playlist_index??-1;
  if(eps&&idx>=0&&idx<eps.length-1) playEpisode(eps[idx+1].file);
}

// ── Playback card ─────────────────────────────────────────────────────────────
let _lastArtUrl = '';
function updatePlaybackCard(){
  const ap  = state.active_player || 'none';
  const st  = state.state || 'idle';
  const pos = state.position || 0;
  const dur = state.duration  || 0;

  // Player badge
  const pl = document.getElementById('m-player');
  if(pl){ pl.className='player-badge '+ap; pl.textContent=ap; }

  // Status
  const stEl = document.getElementById('m-status');
  if(stEl){ stEl.className='status-text '+st; stEl.textContent=st; }

  // Mobile status dot
  const dot = document.getElementById('mob-status-dot');

  // Title
  const ti = document.getElementById('m-title');
  if(ti) ti.textContent = state.title || '—';

  // Year
  const yr = document.getElementById('m-year');
  if(yr) yr.textContent = state.year ? String(state.year) : '—';

  // Datetime (current local time)
  const dt = document.getElementById('m-datetime');
  if(dt){
    const now=new Date();
    dt.textContent = '📅 '
      + String(now.getDate()).padStart(2,'0')+'.'
      + String(now.getMonth()+1).padStart(2,'0')+'.'
      + String(now.getFullYear()).slice(2)+', '
      + pad2(now.getHours())+':'+pad2(now.getMinutes());
  }

  // Progress bar
  const fill = document.getElementById('progress-fill');
  if(fill) fill.style.width = (dur>0 ? (pos/dur*100).toFixed(2) : 0)+'%';
  const posEl=document.getElementById('m-pos'), durEl=document.getElementById('m-dur');
  if(posEl) posEl.textContent=fmtTime(pos);
  if(durEl) durEl.textContent=fmtTime(dur);

  // Artwork — only update src when URL actually changes to avoid flicker
  const artEl=document.getElementById('artwork');
  if(artEl){
    if(state.artwork_url && state.artwork_url!==_lastArtUrl){
      _lastArtUrl=state.artwork_url;
      artEl.src=state.artwork_url+'?t='+Date.now();
      artEl.style.display='block';
    } else if(!state.artwork_url){
      artEl.style.display='none'; artEl.src=''; _lastArtUrl='';
    }
  }
}

// ── DETAILS table ─────────────────────────────────────────────────────────────
const PLAY_KEYS = ['media_type','tv_show','season','episode','rating',
                   'volume','muted','shuffle','repeat'];
const VIDEO_KEYS = ['video_width','video_height','video_fps','hdr','video_codec','video_bitrate_kbps'];

function renderTable(id, keys){
  const rows = keys.map(k => {
    if((k==='tv_show'||k==='season'||k==='episode')
        && state.media_type!=='episode' && !state.tv_show) return '';
    if(k==='rating' && !state.rating) return '';
    // Volume: render as slider
    if(k==='volume'){
      const v=state.volume||0;
      return `<tr><td>${t('lbl_volume')}</td><td>
        <div style="display:flex;align-items:center;gap:6px">
          <input type="range" min="0" max="100" value="${v}"
            style="flex:1;accent-color:#2563c0;cursor:pointer"
            oninput="cmd('set_volume',parseInt(this.value))">
          <span style="min-width:34px;text-align:right;font-size:.78rem;color:#888">${v} %</span>
        </div></td></tr>`;
    }
    return `<tr><td>${t('lbl_'+k)}</td><td>${fmtVal(k,state[k])}</td></tr>`;
  }).join('');
  const el=document.getElementById(id);
  if(el) el.innerHTML=rows;
}

// ── Track selects ─────────────────────────────────────────────────────────────
let _audioHash='', _subHash='';
function renderTracks(){
  const audio=state.audio_tracks||[], sub=state.subtitle_tracks||[];
  const curA=state.current_audio??0, curS=state.current_subtitle??-1;
  const curCh=state.current_chapter??0, chapters=state.chapters||[];

  // Audio select — only rebuild options when list changes
  const aHash=JSON.stringify(audio);
  const selA=document.getElementById('sel-audio');
  if(selA){
    if(aHash!==_audioHash){
      _audioHash=aHash;
      selA.innerHTML=audio.length
        ? audio.map((tr,i)=>`<option value="${i}">${tr.label||('Track '+(i+1))}</option>`).join('')
        : '<option value="">—</option>';
    }
    selA.value=String(curA);
    selA.disabled=audio.length===0;
  }

  // Subtitle select
  const sHash=JSON.stringify(sub);
  const selS=document.getElementById('sel-subtitle');
  if(selS){
    if(sHash!==_subHash){
      _subHash=sHash;
      const opts=['<option value="-1">— Off —</option>'];
      sub.forEach((tr,i)=>opts.push(`<option value="${i}">${tr.label||('Track '+(i+1))}</option>`));
      selS.innerHTML=opts.join('');
    }
    selS.value=String(curS);
    selS.disabled=sub.length===0;
  }

  // Chapter text
  const chEl=document.getElementById('chapter-display');
  if(chEl){
    if(chapters.length && curCh>=0 && curCh<chapters.length){
      chEl.textContent=chapters[curCh].name||('Chapter '+(curCh+1));
    } else {
      chEl.textContent='—';
    }
  }
}

// ── Watched button ────────────────────────────────────────────────────────────
function updateWatchedBtn(){
  const btn=document.getElementById('btn-watched');
  if(!btn) return;
  const has=state.media_id>0&&(state.media_type==='movie'||state.media_type==='episode');
  btn.style.display=has?'':'none';
  if(has) btn.textContent=state.playcount>0?t('btn_watched_on'):t('btn_watched');
}

// ── Season/episode list ───────────────────────────────────────────────────────
let _epScrolledIdx=-2, _epRenderedLen=-1, _epRenderedIdx=-2;
let _seasonOnDesktop=true;

function _ensureSeasonPlacement(){
  const card=document.getElementById('card-season');
  if(!card) return;
  const mobile=window.innerWidth<=900;
  const slot=document.getElementById('season-mobile-slot');
  const panel=document.getElementById('panel-season');
  if(mobile && slot && card.parentElement!==slot){
    slot.appendChild(card);
    _seasonOnDesktop=false;
  } else if(!mobile && panel && card.parentElement!==panel){
    panel.appendChild(card);
    _seasonOnDesktop=true;
  }
}

function renderSeasonEpisodes(){
  _ensureSeasonPlacement();
  const card=document.getElementById('card-season');
  const hdr =document.getElementById('season-hdr');
  const list=document.getElementById('ep-list');
  if(!card||!hdr||!list) return;

  const eps=state.season_episodes;
  if(!eps||!eps.length){
    card.style.display='none';
    _epRenderedLen=-1; _epRenderedIdx=-2;
    return;
  }
  card.style.display='';

  const season=(eps[0]&&eps[0].season)||state.season||'';
  const show=state.tv_show||'';
  hdr.textContent=t('card_season')+(season?' '+season:'')+
    (show?'  ·  '+show:'')+' ('+eps.length+')';

  const idx=state.playlist_index??-1;
  if(eps.length===_epRenderedLen && idx===_epRenderedIdx){
    const pB=document.getElementById('btn-prev-ep');
    const nB=document.getElementById('btn-next-ep');
    if(pB) pB.disabled=idx<=0;
    if(nB) nB.disabled=idx<0||idx>=eps.length-1;
    return;
  }
  _epRenderedLen=eps.length; _epRenderedIdx=idx;

  list.innerHTML=eps.map((ep,i)=>{
    const isCur=i===idx;
    const isWatched=ep.playcount>0&&!isCur;
    const hasResume=ep.resume_pos>10&&!isWatched;
    let cls='ep-row'+(isCur?' ep-current':'')+(isWatched?' ep-watched':'');
    const fileAttr=(ep.file||'').replace(/&/g,'&amp;').replace(/"/g,'&quot;');
    const numStr=isCur?'▶':'E'+String(ep.episode).padStart(2,'0');
    const title=(ep.title||('Episode '+ep.episode)).replace(/&/g,'&amp;').replace(/</g,'&lt;');
    let badges='';
    if(isWatched) badges+='<span class="ep-badge ep-seen-badge">✓</span>';
    if(hasResume) badges+='<span class="ep-badge ep-resume-badge">⏵ '+fmtResumeTime(ep.resume_pos)+'</span>';
    return '<div class="'+cls+'" data-epfile="'+fileAttr+'">'
      +'<span class="ep-num">'+numStr+'</span>'
      +'<span class="ep-title">'+title+'</span>'
      +badges
      +'<span class="ep-runtime">'+fmtRuntime(ep.runtime)+'</span>'
      +'</div>';
  }).join('');

  list.onclick=e=>{
    const row=e.target.closest('.ep-row');
    if(row&&row.dataset.epfile) playEpisode(row.dataset.epfile);
  };

  const pB=document.getElementById('btn-prev-ep');
  const nB=document.getElementById('btn-next-ep');
  if(pB) pB.disabled=idx<=0;
  if(nB) nB.disabled=idx<0||idx>=eps.length-1;

  if(idx>=0&&idx!==_epScrolledIdx){
    _epScrolledIdx=idx;
    const rows=list.querySelectorAll('.ep-row');
    if(rows[idx]) rows[idx].scrollIntoView({block:'nearest'});
  } else if(idx<0) _epScrolledIdx=-2;
}

// ── Kiosk status ──────────────────────────────────────────────────────────────
let _kioskTimer=null;
async function updateKioskStatus(){
  try{
    const s=await fetch('/api/kiosk/status').then(r=>r.json());
    const kb=document.getElementById('kiosk-btns');
    if(kb) kb.style.display='';
    // mobile buttons
    ['mob-btn-kiosk-kodi','mob-btn-kiosk-windows','mob-btn-kiosk-restart'].forEach(id=>{
      const b=document.getElementById(id); if(b) b.style.display='';
    });
    const bK=document.getElementById('btn-kiosk-kodi');
    const bW=document.getElementById('btn-kiosk-windows');
    if(bK) bK.style.background=s.kodi_running&&s.explorer_hidden?'#1a5c2a':'#1a3d1a';
    if(bW) bW.style.background=!s.explorer_hidden?'#3a3a3a':'#2a2a2a';
  }catch(e){}
}
_kioskTimer=setInterval(updateKioskStatus,5000);
updateKioskStatus();

// ── Log viewer ────────────────────────────────────────────────────────────────
let _logAutoTimer=null;
function toggleLogs(){
  const card=document.getElementById('card-logs');
  if(!card) return;
  const vis=card.style.display!=='none';
  card.style.display=vis?'none':'';
  if(!vis) fetchLogs();
}
async function fetchLogs(){
  const level=(document.getElementById('log-level')||{}).value||'';
  const search=(document.getElementById('log-search')||{}).value||'';
  const count=(document.getElementById('log-count')||{}).value||'50';
  let url='/api/logs?limit='+encodeURIComponent(count);
  if(level)  url+='&level='+encodeURIComponent(level);
  if(search) url+='&search='+encodeURIComponent(search);
  try{
    const d=await fetch(url).then(r=>r.json());
    const out=document.getElementById('log-output');
    if(!out) return;
    out.innerHTML=(d.records||[]).map(r=>{
      const txt=r.msg.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return '<div class="log-ln log-'+r.level+'">'+txt+'</div>';
    }).join('');
    out.scrollTop=out.scrollHeight;
  }catch(e){}
}
(function(){
  const a=document.getElementById('log-auto');
  if(a) a.addEventListener('change',function(){
    clearInterval(_logAutoTimer);
    if(this.checked){_logAutoTimer=setInterval(fetchLogs,2000);fetchLogs();}
  });
  const s=document.getElementById('log-search');
  if(s) s.addEventListener('keydown',e=>{if(e.key==='Enter')fetchLogs();});
})();

// ── Settings ──────────────────────────────────────────────────────────────────
function toggleSettings(){
  const card=document.getElementById('card-settings');
  if(!card) return;
  const vis=card.style.display!=='none';
  card.style.display=vis?'none':'';
  if(!vis) loadSettings();
}
async function loadSettings(){
  try{
    const cfg=await fetch('/api/config').then(r=>r.json());
    syncSettingsUI(cfg);
  }catch(e){}
}
function syncSettingsUI(cfg){
  if(!cfg) return;
  const modeMap={art_movie:cfg.movie_art_mode||'poster',
    art_episode:cfg.episode_art_mode||'poster',art_music:cfg.music_art_mode||'thumb'};
  Object.keys(modeMap).forEach(name=>{
    document.querySelectorAll('input[name="'+name+'"]').forEach(r=>{r.checked=r.value===modeMap[name];});
  });
  const bootVal=cfg.hide_explorer?'kodi':'windows';
  document.querySelectorAll('input[name="boot_target"]').forEach(r=>{r.checked=r.value===bootVal;});
  const inp=document.getElementById('inp_kodi_exe');
  if(inp) inp.value=cfg.kodi_exe_path||'';
}
function saveBootTarget(radio){ saveKioskSetting('hide_explorer',radio.value==='kodi'); }
function saveKioskSetting(key,val){
  const body={}; body[key]=val;
  fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>{});
}
function saveArtMode(configKey,radio){
  const body={}; body[configKey]=radio.value;
  fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}).catch(()=>{});
}

// ── Keyboard shortcuts ────────────────────────────────────────────────────────
document.addEventListener('keydown',e=>{
  if(e.target.tagName==='INPUT'||e.target.tagName==='TEXTAREA'||e.target.tagName==='SELECT') return;
  if(e.key==='['){e.preventDefault();seekCustom(-1);return;}
  if(e.key===']'){e.preventDefault();seekCustom(1);return;}
  const map={ArrowUp:'navigate_up',ArrowDown:'navigate_down',
    ArrowLeft:'navigate_left',ArrowRight:'navigate_right',
    Enter:'navigate_select',Escape:'navigate_back',
    Backspace:'navigate_back',' ':'play_pause'};
  if(map[e.key]){e.preventDefault();cmd(map[e.key]);}
});

// ── Mobile menu toggle ────────────────────────────────────────────────────────
function toggleMobileMenu(){ toggleLogs(); }

window.addEventListener('resize',()=>{_ensureSeasonPlacement();});

// ── renderAll ────────────────────────────────────────────────────────────────
function renderAll(){
  updatePlaybackCard();
  renderTable('tbl-play',  PLAY_KEYS);
  renderTable('tbl-video', VIDEO_KEYS);
  renderTracks();
  renderSeasonEpisodes();
  updateWatchedBtn();
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect(){
  const proto=location.protocol==='https:'?'wss':'ws';
  const ws=new WebSocket(proto+'://'+location.host+'/api/ws');
  const setStatus=(text,cls)=>{
    const b=document.getElementById('status-badge');
    const d=document.getElementById('mob-status-dot');
    if(b){b.textContent=text;b.className='status-badge '+cls;}
    if(d) d.className='mob-status-dot '+cls;
  };
  ws.onopen =()=>setStatus(t('status_connected'),'ok');
  ws.onclose=()=>{setStatus(t('status_reconnecting'),'err');setTimeout(connect,3000);};
  ws.onerror=()=>setStatus(t('status_reconnecting'),'err');
  ws.onmessage=e=>{
    const msg=JSON.parse(e.data);
    if(msg.type==='state_full')  state=msg.data;
    else if(msg.type==='state_patch') Object.assign(state,msg.data);
    renderAll();
  };
}

document.getElementById('status-badge').textContent=t('status_connecting');
connect();
