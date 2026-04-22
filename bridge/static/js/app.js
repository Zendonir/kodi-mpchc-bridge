// ── i18n ─────────────────────────────────────────────────────────────────────
const _LANG = (navigator.language || 'en').slice(0,2).toLowerCase();
const _TR = {
  en:{
    status_connecting:'Connecting…',
    status_connected:'Connected',
    status_reconnecting:'Disconnected – reconnecting…',
    card_controls:'Controls',
    card_playback:'Playback',
    card_details:'Details',
    card_video:'Video Info',
    card_tracks:'Tracks',
    btn_skip_back:'⏪ −1 min',
    btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',
    btn_seek_fwd:'+10s',
    btn_back:'← Back',
    btn_home:'⌂ Home',
    btn_menu:'☰ Menu',
    btn_info:'ℹ Info',
    btn_watched:'☆ Unwatched',
    btn_watched_on:'★ Watched',
    nav_up:'Up (↑)', nav_down:'Down (↓)',
    nav_left:'Left (←)', nav_right:'Right (→)', nav_ok:'OK (Enter)',
    kbd_hint:'Keyboard: <kbd>↑↓←→</kbd> navigate &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Back &nbsp;<kbd>Space</kbd> Play/Pause',
    lbl_active_player:'Player', lbl_state:'Status', lbl_title:'Title',
    lbl_artist:'Artist', lbl_album:'Album', lbl_media_type:'Type',
    lbl_position:'Position', lbl_duration:'Duration', lbl_volume:'Volume',
    lbl_muted:'Muted', lbl_shuffle:'Shuffle', lbl_repeat:'Repeat',
    lbl_year:'Year', lbl_tv_show:'Show', lbl_season:'Season', lbl_episode:'Episode',
    lbl_video_width:'Width', lbl_video_height:'Height', lbl_video_fps:'Frame rate',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Subtitle', lbl_current_chapter:'Chapter',
    val_yes:'Yes', val_no:'No', val_of:'of',
    btn_fullscreen:'⛶ Fullscreen',
    btn_fullscreen_short:'Fullscreen',
    btn_restart_pc:'⏻ Restart PC',
    btn_restart_short:'Restart PC',
    confirm_restart:'Schedule a system restart in 10 seconds?',
    card_season:'Season',
    lbl_ep_resume:'Resume',
    lbl_no_episodes:'No episode data available.',
    btn_prev_ep:'⏮ Prev',
    btn_next_ep:'Next ⏭',
    btn_logs:'\U0001F4CB Log',
    card_logs:'Bridge Log',
    btn_log_refresh:'↻',
    btn_settings:'⚙ Settings',
    btn_settings_short:'Settings',
    card_settings:'Settings',
    lbl_art_movie:'Movie',
    lbl_art_episode:'TV Series',
    lbl_art_music:'Music',
    opt_art_poster:'Poster',
    opt_art_fanart:'Fanart / Backdrop',
    opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Series poster',
    opt_art_seasonposter:'Season poster',
    lbl_kodi_exe:'Kodi path:',
    btn_kiosk_kodi:'Kodi Windows',
    btn_kiosk_kodi_short:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Restart Kodi',
    btn_kiosk_restart_short:'Restart Kodi',
    lbl_boot_target:'Boot target',
    opt_boot_kodi:'Kodi — hide Explorer on startup',
    opt_boot_windows:'Windows — normal desktop',
  },
  de:{
    status_connecting:'Verbinde…',
    status_connected:'Verbunden',
    status_reconnecting:'Getrennt – verbinde erneut…',
    card_controls:'Steuerung',
    card_playback:'Wiedergabe',
    card_details:'Details',
    card_video:'Video-Info',
    card_tracks:'Spuren',
    btn_skip_back:'⏪ −1 min',
    btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',
    btn_seek_fwd:'+10s',
    btn_back:'← Zurück',
    btn_home:'⌂ Home',
    btn_menu:'☰ Menü',
    btn_info:'ℹ Info',
    btn_watched:'☆ Ungesehen',
    btn_watched_on:'★ Gesehen',
    nav_up:'Hoch (↑)', nav_down:'Runter (↓)',
    nav_left:'Links (←)', nav_right:'Rechts (→)', nav_ok:'OK (Enter)',
    kbd_hint:'Tastatur: <kbd>↑↓←→</kbd> navigieren &nbsp;<kbd>Enter</kbd> OK &nbsp;<kbd>Esc</kbd> Zurück &nbsp;<kbd>Leertaste</kbd> Play/Pause',
    lbl_active_player:'Player', lbl_state:'Status', lbl_title:'Titel',
    lbl_artist:'Interpret', lbl_album:'Album', lbl_media_type:'Typ',
    lbl_position:'Position', lbl_duration:'Dauer', lbl_volume:'Lautstärke',
    lbl_muted:'Stumm', lbl_shuffle:'Shuffle', lbl_repeat:'Wiederholen',
    lbl_year:'Jahr', lbl_tv_show:'Serie', lbl_season:'Staffel', lbl_episode:'Folge',
    lbl_video_width:'Breite', lbl_video_height:'Höhe', lbl_video_fps:'Framerate',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio-Spur', lbl_current_subtitle:'Untertitel', lbl_current_chapter:'Kapitel',
    val_yes:'Ja', val_no:'Nein', val_of:'von',
    btn_fullscreen:'⛶ Vollbild',
    btn_fullscreen_short:'Vollbild',
    btn_restart_pc:'⏻ PC neu starten',
    btn_restart_short:'PC neu starten',
    confirm_restart:'PC in 10 Sekunden neu starten?',
    card_season:'Staffel',
    lbl_ep_resume:'Fortsetzen',
    lbl_no_episodes:'Keine Episodendaten verfügbar.',
    btn_prev_ep:'⏮ Zurück',
    btn_next_ep:'Weiter ⏭',
    btn_logs:'\U0001F4CB Log',
    card_logs:'Bridge Log',
    btn_log_refresh:'↻',
    btn_settings:'⚙ Einstellungen',
    btn_settings_short:'Einstellungen',
    card_settings:'Einstellungen',
    lbl_art_movie:'Film',
    lbl_art_episode:'Serien',
    lbl_art_music:'Musik',
    opt_art_poster:'Poster',
    opt_art_fanart:'Fanart / Hintergrund',
    opt_art_thumb:'Thumbnail',
    opt_art_tvposter:'Seriencover',
    opt_art_seasonposter:'Staffelcover',
    lbl_kodi_exe:'Kodi-Pfad:',
    btn_kiosk_kodi:'Kodi Windows',
    btn_kiosk_kodi_short:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Kodi neustarten',
    btn_kiosk_restart_short:'Kodi neustarten',
    lbl_boot_target:'Boot-Ziel',
    opt_boot_kodi:'Kodi — Explorer beim Start verstecken',
    opt_boot_windows:'Windows — normaler Desktop',
  },
  fr:{
    status_connecting:'Connexion…',
    status_connected:'Connecté',
    status_reconnecting:'Déconnecté – reconnexion…',
    card_controls:'Contrôles',
    card_playback:'Lecture',
    card_details:'Détails',
    card_video:'Infos vidéo',
    card_tracks:'Pistes',
    btn_skip_back:'⏪ −1 min',
    btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',
    btn_seek_fwd:'+10s',
    btn_back:'← Retour',
    btn_home:'⌂ Accueil',
    btn_menu:'☰ Menu',
    btn_info:'ℹ Infos',
    btn_watched:'☆ Non vu',
    btn_watched_on:'★ Vu',
    nav_up:'Haut (↑)', nav_down:'Bas (↓)',
    nav_left:'Gauche (←)', nav_right:'Droite (→)', nav_ok:'OK (Entrée)',
    kbd_hint:'Clavier : <kbd>↑↓←→</kbd> naviguer &nbsp;<kbd>Entrée</kbd> OK &nbsp;<kbd>Échap</kbd> Retour &nbsp;<kbd>Espace</kbd> Lecture/Pause',
    lbl_active_player:'Lecteur', lbl_state:'État', lbl_title:'Titre',
    lbl_artist:'Artiste', lbl_album:'Album', lbl_media_type:'Type',
    lbl_position:'Position', lbl_duration:'Durée', lbl_volume:'Volume',
    lbl_muted:'Muet', lbl_shuffle:'Aléatoire', lbl_repeat:'Répéter',
    lbl_year:'Année', lbl_tv_show:'Série', lbl_season:'Saison', lbl_episode:'Épisode',
    lbl_video_width:'Largeur', lbl_video_height:'Hauteur', lbl_video_fps:'Fréquence',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Débit',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Sous-titres', lbl_current_chapter:'Chapitre',
    val_yes:'Oui', val_no:'Non', val_of:'sur',
    btn_fullscreen:'⛶ Plein écran',
    btn_fullscreen_short:'Plein écran',
    btn_restart_pc:'⏻ Redémarrer le PC',
    btn_restart_short:'Redémarrer',
    confirm_restart:'Planifier un redémarrage dans 10 secondes ?',
    card_season:'Saison',
    lbl_ep_resume:'Reprendre',
    lbl_no_episodes:'Aucune donnée d’épisode.',
    btn_prev_ep:'⏮ Préc',
    btn_next_ep:'Suiv ⏭',
    btn_logs:'\U0001F4CB Journal',
    card_logs:'Journal Bridge',
    btn_log_refresh:'↻',
    btn_settings:'⚙ Réglages',
    btn_settings_short:'Réglages',
    card_settings:'Réglages',
    lbl_art_movie:'Film',
    lbl_art_episode:'Série TV',
    lbl_art_music:'Musique',
    opt_art_poster:'Affiche',
    opt_art_fanart:'Fanart / Fond',
    opt_art_thumb:'Miniature',
    opt_art_tvposter:'Affiche de série',
    opt_art_seasonposter:'Affiche de saison',
    lbl_kodi_exe:'Chemin Kodi :',
    btn_kiosk_kodi:'Kodi Windows',
    btn_kiosk_kodi_short:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Redém. Kodi',
    btn_kiosk_restart_short:'Redém. Kodi',
    lbl_boot_target:'Cible de démarrage',
    opt_boot_kodi:'Kodi — masquer l’Explorateur',
    opt_boot_windows:'Windows — bureau normal',
  },
  es:{
    status_connecting:'Conectando…',
    status_connected:'Conectado',
    status_reconnecting:'Desconectado – reconectando…',
    card_controls:'Controles',
    card_playback:'Reproducción',
    card_details:'Detalles',
    card_video:'Info de vídeo',
    card_tracks:'Pistas',
    btn_skip_back:'⏪ −1 min',
    btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',
    btn_seek_fwd:'+10s',
    btn_back:'← Volver',
    btn_home:'⌂ Inicio',
    btn_menu:'☰ Menú',
    btn_info:'ℹ Info',
    btn_watched:'☆ No visto',
    btn_watched_on:'★ Visto',
    nav_up:'Arriba (↑)', nav_down:'Abajo (↓)',
    nav_left:'Izquierda (←)', nav_right:'Derecha (→)', nav_ok:'OK (Intro)',
    kbd_hint:'Teclado: <kbd>↑↓←→</kbd> navegar &nbsp;<kbd>Intro</kbd> OK &nbsp;<kbd>Esc</kbd> Volver &nbsp;<kbd>Espacio</kbd> Play/Pausa',
    lbl_active_player:'Reproductor', lbl_state:'Estado', lbl_title:'Título',
    lbl_artist:'Artista', lbl_album:'Álbum', lbl_media_type:'Tipo',
    lbl_position:'Posición', lbl_duration:'Duración', lbl_volume:'Volumen',
    lbl_muted:'Silencio', lbl_shuffle:'Aleatorio', lbl_repeat:'Repetir',
    lbl_year:'Año', lbl_tv_show:'Serie', lbl_season:'Temporada', lbl_episode:'Episodio',
    lbl_video_width:'Ancho', lbl_video_height:'Alto', lbl_video_fps:'Fotogramas',
    lbl_hdr:'HDR', lbl_video_codec:'Códec', lbl_video_bitrate_kbps:'Tasa de bits',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Subtítulos', lbl_current_chapter:'Capítulo',
    val_yes:'Sí', val_no:'No', val_of:'de',
    btn_fullscreen:'⛶ Pantalla completa',
    btn_fullscreen_short:'Pantalla completa',
    btn_restart_pc:'⏻ Reiniciar PC',
    btn_restart_short:'Reiniciar',
    confirm_restart:'¿Reiniciar el sistema en 10 segundos?',
    card_season:'Temporada',
    lbl_ep_resume:'Reanudar',
    lbl_no_episodes:'Sin datos de episodios.',
    btn_prev_ep:'⏮ Ant',
    btn_next_ep:'Sig ⏭',
    btn_logs:'\U0001F4CB Registro',
    card_logs:'Registro Bridge',
    btn_log_refresh:'↻',
    btn_settings:'⚙ Ajustes',
    btn_settings_short:'Ajustes',
    card_settings:'Ajustes',
    lbl_art_movie:'Película',
    lbl_art_episode:'Serie TV',
    lbl_art_music:'Música',
    opt_art_poster:'Póster',
    opt_art_fanart:'Fanart / Fondo',
    opt_art_thumb:'Miniatura',
    opt_art_tvposter:'Póster de serie',
    opt_art_seasonposter:'Póster de temporada',
    lbl_kodi_exe:'Ruta de Kodi:',
    btn_kiosk_kodi:'Kodi Windows',
    btn_kiosk_kodi_short:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Reiniciar Kodi',
    btn_kiosk_restart_short:'Reiniciar Kodi',
    lbl_boot_target:'Destino de arranque',
    opt_boot_kodi:'Kodi — ocultar Explorador',
    opt_boot_windows:'Windows — escritorio normal',
  },
  it:{
    status_connecting:'Connessione…',
    status_connected:'Connesso',
    status_reconnecting:'Disconnesso – riconnessione…',
    card_controls:'Controlli',
    card_playback:'Riproduzione',
    card_details:'Dettagli',
    card_video:'Info video',
    card_tracks:'Tracce',
    btn_skip_back:'⏪ −1 min',
    btn_skip_fwd:'+1 min ⏩',
    btn_seek_back:'−10s',
    btn_seek_fwd:'+10s',
    btn_back:'← Indietro',
    btn_home:'⌂ Home',
    btn_menu:'☰ Menu',
    btn_info:'ℹ Info',
    btn_watched:'☆ Non visto',
    btn_watched_on:'★ Visto',
    nav_up:'Su (↑)', nav_down:'Giù (↓)',
    nav_left:'Sinistra (←)', nav_right:'Destra (→)', nav_ok:'OK (Invio)',
    kbd_hint:'Tastiera: <kbd>↑↓←→</kbd> navigare &nbsp;<kbd>Invio</kbd> OK &nbsp;<kbd>Esc</kbd> Indietro &nbsp;<kbd>Spazio</kbd> Play/Pausa',
    lbl_active_player:'Lettore', lbl_state:'Stato', lbl_title:'Titolo',
    lbl_artist:'Artista', lbl_album:'Album', lbl_media_type:'Tipo',
    lbl_position:'Posizione', lbl_duration:'Durata', lbl_volume:'Volume',
    lbl_muted:'Muto', lbl_shuffle:'Casuale', lbl_repeat:'Ripeti',
    lbl_year:'Anno', lbl_tv_show:'Serie', lbl_season:'Stagione', lbl_episode:'Episodio',
    lbl_video_width:'Larghezza', lbl_video_height:'Altezza', lbl_video_fps:'Fotogrammi',
    lbl_hdr:'HDR', lbl_video_codec:'Codec', lbl_video_bitrate_kbps:'Bitrate',
    lbl_current_audio:'Audio', lbl_current_subtitle:'Sottotitoli', lbl_current_chapter:'Capitolo',
    val_yes:'Sì', val_no:'No', val_of:'di',
    btn_fullscreen:'⛶ Schermo intero',
    btn_fullscreen_short:'Schermo intero',
    btn_restart_pc:'⏻ Riavvia PC',
    btn_restart_short:'Riavvia',
    confirm_restart:'Pianificare il riavvio tra 10 secondi?',
    card_season:'Stagione',
    lbl_ep_resume:'Riprendi',
    lbl_no_episodes:'Nessun dato episodio.',
    btn_prev_ep:'⏮ Prec',
    btn_next_ep:'Succ ⏭',
    btn_logs:'\U0001F4CB Log',
    card_logs:'Log Bridge',
    btn_log_refresh:'↻',
    btn_settings:'⚙ Impostazioni',
    btn_settings_short:'Impostazioni',
    card_settings:'Impostazioni',
    lbl_art_movie:'Film',
    lbl_art_episode:'Serie TV',
    lbl_art_music:'Musica',
    opt_art_poster:'Locandina',
    opt_art_fanart:'Fanart / Sfondo',
    opt_art_thumb:'Miniatura',
    opt_art_tvposter:'Locandina serie',
    opt_art_seasonposter:'Locandina stagione',
    lbl_kodi_exe:'Percorso Kodi:',
    btn_kiosk_kodi:'Kodi Windows',
    btn_kiosk_kodi_short:'Kodi',
    btn_kiosk_windows:'Windows',
    btn_kiosk_restart:'Riavvia Kodi',
    btn_kiosk_restart_short:'Riavvia Kodi',
    lbl_boot_target:'Destinazione avvio',
    opt_boot_kodi:'Kodi — nascondi Explorer',
    opt_boot_windows:'Windows — desktop normale',
  },
};
const _T = _TR[_LANG] || _TR.en;
function t(k){ return (_T[k] !== undefined ? _T[k] : _TR.en[k]) || k; }

// Apply static translations to the DOM
(function applyI18n(){
  document.querySelectorAll('[data-i18n]').forEach(el => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll('[data-i18n-html]').forEach(el => {
    el.innerHTML = t(el.dataset.i18nHtml);
  });
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = t(el.dataset.i18nTitle);
  });
  document.getElementById('status').textContent = t('status_connecting');
})();

// ── State ─────────────────────────────────────────────────────────────────────
const DETAIL_KEYS = [
  'year','media_type','tv_show','season','episode',
  'artist','album','position','duration','volume','muted','shuffle','repeat'
];
const VIDEO_KEYS  = ['video_width','video_height','video_fps','hdr','video_codec','video_bitrate_kbps'];
const TRACK_KEYS  = ['current_audio','current_subtitle','current_chapter'];

let state = {};

function fmtTime(secs) {
  const s = Math.round(secs || 0);
  return new Date(s * 1000).toISOString().substr(11, 8);
}

function fmt(k, v) {
  if (v === null || v === undefined) return '—';
  if (k === 'position' || k === 'duration') return fmtTime(v);
  if (k === 'volume') {
    const pct = Math.min(100, Math.max(0, v || 0));
    return '<span class="vol-row">'
         + '<span class="vol-bg"><span class="vol-fill" style="width:' + pct + '%"></span></span>'
         + '<span class="vol-val">' + pct + ' %</span></span>';
  }
  if (k === 'video_fps') return v ? v.toFixed(3) + ' fps' : '—';
  if (k === 'video_bitrate_kbps') return v ? (v / 1000).toFixed(1) + ' Mbps' : '—';
  if (k === 'video_width' || k === 'video_height') return v ? v + ' px' : '—';
  if (k === 'year') return v ? String(v) : '—';
  if (k === 'season') {
    if (!v) return '—';
    return state.season_count > 0 ? v + ' ' + t('val_of') + ' ' + state.season_count : String(v);
  }
  if (k === 'episode') {
    if (!v) return '—';
    return state.episode_count > 0 ? v + ' ' + t('val_of') + ' ' + state.episode_count : String(v);
  }
  if (typeof v === 'boolean') return v ? t('val_yes') : t('val_no');
  if (Array.isArray(v)) return v.length ? v.map(x => x.label || x.name || '?').join(', ') : '—';
  return v ? String(v) : '—';
}

function label(k) { return t('lbl_' + k) || k; }

function renderTable(id, keys) {
  const rows = keys.map(k => {
    const v = fmt(k, state[k]);
    if ((k === 'tv_show' || k === 'season' || k === 'episode') &&
        state.media_type !== 'episode' && !state.tv_show) return '';
    if ((k === 'artist' || k === 'album') &&
        state.media_type !== 'music' && !state.artist && !state.album) return '';
    return '<tr><td>' + label(k) + '</td><td>' + v + '</td></tr>';
  }).join('');
  document.getElementById(id).innerHTML = rows;
}

function renderPlaybackHeader() {
  const player = state.active_player || 'none';
  const status = state.state || '';
  const title  = state.title || '—';
  const year   = state.year  ? String(state.year) : '—';
  const pos    = state.position || 0;
  const dur    = state.duration || 0;

  const pEl = document.getElementById('pb-player');
  if (pEl) { pEl.textContent = player; pEl.className = 'player-badge player-' + player; }

  const sEl = document.getElementById('pb-status');
  if (sEl) { sEl.textContent = status || '—'; sEl.className = 'pb-status pb-status-' + status; }

  const tEl = document.getElementById('pb-title');
  if (tEl) tEl.textContent = title;

  const yEl = document.getElementById('pb-year');
  if (yEl) yEl.textContent = year;

  const fill = document.getElementById('progress-fill');
  if (fill) fill.style.width = (dur > 0 ? Math.min(100, (pos / dur) * 100) : 0) + '%';

  const posEl = document.getElementById('pb-position');
  if (posEl) posEl.textContent = fmtTime(pos);

  const durEl = document.getElementById('pb-duration');
  if (durEl) durEl.textContent = fmtTime(dur);
}

function updateClock() {
  const el = document.getElementById('pb-clock');
  if (!el) return;
  const now = new Date();
  const d = now.toLocaleDateString(undefined, {year:'2-digit', month:'2-digit', day:'2-digit'});
  const h = now.getHours().toString().padStart(2,'0');
  const m = now.getMinutes().toString().padStart(2,'0');
  el.textContent = d + ', ' + h + ':' + m;
}
setInterval(updateClock, 30000);
updateClock();

function updateWatchedBtn() {
  const btn = document.getElementById('btn-watched');
  if (!btn) return;
  const hasItem = state.media_id > 0 &&
    (state.media_type === 'movie' || state.media_type === 'episode');
  btn.style.display = hasItem ? '' : 'none';
  if (hasItem) btn.textContent = state.playcount > 0 ? t('btn_watched_on') : t('btn_watched');
}

function renderAll() {
  renderPlaybackHeader();
  renderTable('tbl-play',   DETAIL_KEYS);
  renderTable('tbl-video',  VIDEO_KEYS);

  // Track table with label lookup
  const trackRows = TRACK_KEYS.map(k => {
    let display = fmt(k, state[k]);
    const listKey = k.replace('current_audio','audio_tracks')
                     .replace('current_subtitle','subtitle_tracks')
                     .replace('current_chapter','chapters');
    const arr = state[listKey] || [];
    if (arr.length) {
      const item = arr[state[k]];
      if (item) display = item.label || item.name || display;
    }
    return '<tr><td>' + label(k) + '</td><td>' + display + '</td></tr>';
  }).join('');
  document.getElementById('tbl-tracks').innerHTML = trackRows;

  // Artwork
  const artEl = document.getElementById('artwork');
  if (state.artwork_url) {
    artEl.src = state.artwork_url + '?t=' + Date.now();
    artEl.style.display = 'block';
  } else {
    artEl.style.display = 'none';
    artEl.src = '';
  }

  renderSeasonEpisodes();
  updateWatchedBtn();
}

// ── Commands ──────────────────────────────────────────────────────────────────
function cmd(c, val) {
  const body = {cmd: c};
  if (val !== undefined) body.value = val;
  fetch('/api/command', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(() => {});
}

function restartConfirm() {
  if (confirm(t('confirm_restart'))) { cmd('system_restart'); }
}

// ── Kiosk ─────────────────────────────────────────────────────────────────────
function kioskCmd(mode) {
  fetch('/api/kiosk/' + mode, {method:'POST'}).catch(() => {});
  setTimeout(updateKioskStatus, 4000);
}

let _kioskTimer = null;
async function updateKioskStatus() {
  try {
    const s = await fetch('/api/kiosk/status').then(r => r.json());
    const btns = document.getElementById('kiosk-btns');
    if (btns) btns.style.display = '';
    const bKodi = document.getElementById('btn-kiosk-kodi');
    const bWin  = document.getElementById('btn-kiosk-windows');
    if (bKodi) bKodi.style.background = (s.kodi_running && s.explorer_hidden) ? '#1a5c2a' : '';
    if (bWin)  bWin.style.background  = (!s.explorer_hidden) ? '#3a3a3a' : '';
    // mirror on mobile bar buttons
    const mKodi = document.getElementById('btn-kiosk-kodi-mob');
    if (mKodi) mKodi.style.opacity = (s.kodi_running && s.explorer_hidden) ? '1' : '0.6';
  } catch(e) {}
}
_kioskTimer = setInterval(updateKioskStatus, 5000);
updateKioskStatus();

// ── Keyboard ──────────────────────────────────────────────────────────────────
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === '[') { e.preventDefault(); cmd('seek_relative', -30); return; }
  if (e.key === ']') { e.preventDefault(); cmd('seek_relative',  30); return; }
  const map = {
    ArrowUp:'navigate_up', ArrowDown:'navigate_down',
    ArrowLeft:'navigate_left', ArrowRight:'navigate_right',
    Enter:'navigate_select', Escape:'navigate_back',
    Backspace:'navigate_back', ' ':'play_pause',
  };
  if (map[e.key]) { e.preventDefault(); cmd(map[e.key]); }
});

// ── Sidebar toggle (mobile) ───────────────────────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  if (sb) sb.classList.toggle('open');
}

// ── Log viewer ────────────────────────────────────────────────────────────────
let _logAutoTimer = null;

function toggleLogs() {
  const card = document.getElementById('card-logs');
  if (!card) return;
  const visible = card.style.display !== 'none';
  card.style.display = visible ? 'none' : '';
  if (!visible) fetchLogs();
}

async function fetchLogs() {
  const level  = (document.getElementById('log-level')  || {}).value || '';
  const search = (document.getElementById('log-search') || {}).value || '';
  const count  = (document.getElementById('log-count')  || {}).value || '50';
  let url = '/api/logs?limit=' + encodeURIComponent(count);
  if (level)  url += '&level='  + encodeURIComponent(level);
  if (search) url += '&search=' + encodeURIComponent(search);
  try {
    const d = await fetch(url).then(r => r.json());
    const out = document.getElementById('log-output');
    if (!out) return;
    const recs = d.records || [];
    out.innerHTML = recs.map(function(r) {
      const txt = r.msg
        .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      return '<div class="log-ln log-' + r.level + '">' + txt + '</div>';
    }).join('');
    out.scrollTop = out.scrollHeight;
  } catch(e) {}
}

(function _setupLogListeners() {
  var autoChk = document.getElementById('log-auto');
  if (autoChk) {
    autoChk.addEventListener('change', function() {
      clearInterval(_logAutoTimer);
      if (this.checked) { _logAutoTimer = setInterval(fetchLogs, 2000); fetchLogs(); }
    });
  }
  var srch = document.getElementById('log-search');
  if (srch) { srch.addEventListener('keydown', function(e){ if(e.key==='Enter') fetchLogs(); }); }
}());

// ── Settings ──────────────────────────────────────────────────────────────────
function toggleSettings() {
  const card = document.getElementById('card-settings');
  if (!card) return;
  const visible = card.style.display !== 'none';
  card.style.display = visible ? 'none' : '';
  if (!visible) loadSettings();
}

async function loadSettings() {
  try {
    const cfg = await fetch('/api/config').then(r => r.json());
    syncSettingsUI(cfg);
  } catch(e) {}
}

function syncSettingsUI(cfg) {
  if (!cfg) return;
  const modeMap = {
    art_movie:   cfg.movie_art_mode   || 'poster',
    art_episode: cfg.episode_art_mode || 'poster',
    art_music:   cfg.music_art_mode   || 'thumb',
  };
  Object.keys(modeMap).forEach(function(name) {
    document.querySelectorAll('input[name="' + name + '"]').forEach(function(r) {
      r.checked = r.value === modeMap[name];
    });
  });
  const bootVal = cfg.hide_explorer ? 'kodi' : 'windows';
  document.querySelectorAll('input[name="boot_target"]').forEach(function(r) {
    r.checked = r.value === bootVal;
  });
  const inpKodi = document.getElementById('inp_kodi_exe');
  if (inpKodi) inpKodi.value = cfg.kodi_exe_path || '';
}

function saveBootTarget(radio) {
  saveKioskSetting('hide_explorer', radio.value === 'kodi');
}

function saveKioskSetting(key, val) {
  const body = {};
  body[key] = val;
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(() => {});
}

function saveArtMode(configKey, radio) {
  const body = {};
  body[configKey] = radio.value;
  fetch('/api/config', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(body),
  }).catch(() => {});
}

// ── Episode navigation ────────────────────────────────────────────────────────
function prevEpisode() {
  const eps = state.season_episodes;
  const idx = state.playlist_index != null ? state.playlist_index : -1;
  if (!eps || idx <= 0) return;
  playEpisode(eps[idx - 1].file);
}

function nextEpisode() {
  const eps = state.season_episodes;
  const idx = state.playlist_index != null ? state.playlist_index : -1;
  if (!eps || idx < 0 || idx >= eps.length - 1) return;
  playEpisode(eps[idx + 1].file);
}

function fmtRuntime(secs) {
  if (!secs) return '';
  return Math.round(secs / 60) + ' min';
}

function fmtResumeTime(secs) {
  if (!secs) return '';
  const s = Math.round(secs);
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  return h > 0
    ? h + ':' + String(m).padStart(2,'0') + ':' + String(ss).padStart(2,'0')
    : m + ':' + String(ss).padStart(2,'0');
}

function renderSeasonEpisodes() {
  const card = document.getElementById('card-season');
  const hdr  = document.getElementById('season-hdr');
  const list = document.getElementById('ep-list');
  if (!card || !hdr || !list) return;

  const eps = state.season_episodes;
  if (!eps || !eps.length) { card.style.display = 'none'; return; }
  card.style.display = '';

  const season = (eps[0] && eps[0].season) ? eps[0].season : (state.season || '');
  const show   = state.tv_show || '';
  hdr.textContent =
    t('card_season') + (season ? ' ' + season : '') +
    (show ? '  ·  ' + show : '') +
    '  (' + eps.length + ')';

  const idx = state.playlist_index != null ? state.playlist_index : -1;

  list.innerHTML = eps.map((ep, i) => {
    const isCur     = i === idx;
    const isWatched = ep.playcount > 0 && !isCur;
    const hasResume = ep.resume_pos > 10 && !isWatched;

    let cls = 'ep-row';
    if (isCur)     cls += ' ep-current';
    if (isWatched) cls += ' ep-watched';

    const fileAttr = (ep.file || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;');
    const numStr   = 'E' + String(ep.episode).padStart(2,'0');
    const title    = (ep.title || ('Episode ' + ep.episode))
                       .replace(/&/g,'&amp;').replace(/</g,'&lt;');
    const runtime  = fmtRuntime(ep.runtime);

    let badges = '';
    if (isCur) {
      badges += '<span class="ep-badge ep-seen">&#x25B6;</span>';
    } else if (isWatched) {
      badges += '<span class="ep-badge ep-seen">&#x2713;</span>';
    }
    if (hasResume) {
      badges += '<span class="ep-badge ep-resume">&#x23F5; ' + fmtResumeTime(ep.resume_pos) + '</span>';
    }

    return '<div class="' + cls + '" data-epfile="' + fileAttr + '">'
      + '<span class="ep-num">'     + numStr  + '</span>'
      + '<span class="ep-title">'   + title   + '</span>'
      + badges
      + '<span class="ep-runtime">' + runtime + '</span>'
      + '</div>';
  }).join('');

  list.onclick = function(e) {
    const row = e.target.closest('.ep-row');
    if (row && row.dataset.epfile) playEpisode(row.dataset.epfile);
  };

  const prevBtn = document.getElementById('btn-prev-ep');
  const nextBtn = document.getElementById('btn-next-ep');
  if (prevBtn) prevBtn.disabled = idx <= 0;
  if (nextBtn) nextBtn.disabled = idx < 0 || idx >= eps.length - 1;

  if (idx >= 0) {
    const rows = list.querySelectorAll('.ep-row');
    if (rows[idx]) rows[idx].scrollIntoView({block: 'nearest'});
  }
}

function playEpisode(filepath) {
  fetch('/api/external_play', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({filepath: filepath}),
  }).catch(() => {});
}

// ── WebSocket ─────────────────────────────────────────────────────────────────
function connect() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws  = new WebSocket(proto + '://' + location.host + '/api/ws');
  const el  = document.getElementById('status');

  ws.onopen  = () => { el.textContent = t('status_connected');     el.className = 'ok';  };
  ws.onclose = () => {
    el.textContent = t('status_reconnecting'); el.className = 'err';
    setTimeout(connect, 3000);
  };
  ws.onerror = () => { el.className = 'err'; };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if      (msg.type === 'state_full')  { state = msg.data; }
    else if (msg.type === 'state_patch') { Object.assign(state, msg.data); }
    renderAll();
  };
}

connect();
