"""
Internationalisation module for kodi-mpchc-bridge.

Detects the Windows UI language once at import time and exposes a T()
function that resolves translation keys for the active language.

Supported languages
-------------------
    en  English   (default / fallback)
    de  German
    fr  French
    es  Spanish
    it  Italian

Usage
-----
    from bridge.i18n import T, LANG

    print(T("tray_quit"))          # "Beenden" on a German OS
    print(T("tray_running", port=13590))
"""

from __future__ import annotations

import locale
import sys

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def _detect_lang() -> str:
    """Return a 2-letter lowercase language code for the current OS UI."""
    if sys.platform == "win32":
        try:
            import ctypes
            lcid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            loc_str = locale.windows_locale.get(lcid, "en_US")
            return loc_str[:2].lower()
        except Exception:
            pass
    try:
        loc_str = locale.getdefaultlocale()[0] or "en"
        return loc_str[:2].lower()
    except Exception:
        return "en"


# Active language code (e.g. "de", "en", "fr", "es", "it")
LANG: str = _detect_lang()

# ---------------------------------------------------------------------------
# Translation tables
# ---------------------------------------------------------------------------

_STRINGS: dict[str, dict[str, str]] = {

    # ── English ───────────────────────────────────────────────────────────────
    "en": {
        # Tray icon
        "tray_open_test":   "Open Test Interface",
        "tray_settings":    "Settings\u2026",
        "tray_quit":        "Quit",
        "tray_starting":    "kodi-mpchc-bridge \u2014 starting\u2026",
        "tray_running":     "kodi-mpchc-bridge \u2014 running  (port {port})",
        "tray_stopped":     "kodi-mpchc-bridge \u2014 stopped  (port {port})",

        # Settings dialog
        "settings_title":          "Settings \u2014 Kodi-MPC-HC Bridge",
        "settings_kodi_section":   "Kodi Connection",
        "settings_bridge_section": "Bridge Server",
        "settings_host":           "Host",
        "settings_http_port":      "HTTP Port",
        "settings_ws_port":        "WebSocket Port",
        "settings_username":       "Username",
        "settings_password":       "Password",
        "settings_mpchc_port":     "MPC-HC Port",
        "settings_bridge_port":    "Bridge Port",
        "settings_auth_hint":      "Leave username/password empty if Kodi requires no authentication.",
        "btn_save":                "\U0001f4be  Save",
        "btn_cancel":              "Cancel",
        "saved_title":             "Saved",
        "saved_msg":               (
            "Settings saved.\n"
            "Restart the bridge (Quit \u2192 reopen) for the changes to take effect."
        ),
        "err_title":               "Error",
        "err_no_config":           "Config manager not available.",
        "err_invalid_input":       "Invalid input",
        "err_int_expected":        "{key}: integer expected.",
        "err_test_client":         "Could not launch test interface:\n{exc}",

        # Test client
        "tc_window_title":   "kodi-mpchc-bridge  \u2014  Test Client",
        "tc_now_playing":    " Now Playing ",
        "tc_playback":       " Playback ",
        "tc_volume_panel":   " Volume ",
        "tc_tracks_panel":   " Tracks ",
        "tc_nav_panel":      " Navigation ",
        "tc_state_lbl":      "State",
        "tc_title_lbl":      "Title",
        "tc_artist_lbl":     "Artist",
        "tc_album_lbl":      "Album",
        "tc_type_lbl":       "Type",
        "tc_pos_lbl":        "Position",
        "tc_dur_lbl":        "Duration",
        "tc_vol_lbl":        "Volume",
        "tc_muted_lbl":      "Muted",
        "tc_shuffle_lbl":    "Shuffle",
        "tc_repeat_lbl":     "Repeat",
        "tc_cover_lbl":      "Cover",
        "tc_seek_lbl":       "Seek to (s)",
        "tc_audio_lbl":      "Audio",
        "tc_sub_lbl":        "Subtitle",
        "tc_chapter_lbl":    "Chapter",
        "tc_log_lbl":        "Log",
        "tc_connected":      "\u25cf Connected",
        "tc_disconnected":   "\u25cf Disconnected",
        "tc_bridge_lbl":     "Bridge:",
        "tc_pillow_missing": "(Pillow not installed)",
        "tc_off":            "Off",

        # MPC Proxy settings
        "settings_proxy_section":   "MPC Proxy (Optional)",
        "settings_proxy_enabled":   "Enable MPC Proxy",
        "settings_proxy_path":      "Proxy Executable",
        "btn_browse":               "Browse\u2026",
        "settings_proxy_setup_btn": "Setup Kodi Player",
        "settings_proxy_setup_ok":  "playercorefactory.xml written to:\n{path}",
        "settings_proxy_setup_err": "Setup failed:\n{err}",
        "settings_proxy_no_path":   "Please enter the path to the MPC Proxy executable first.",
    },

    # ── German ────────────────────────────────────────────────────────────────
    "de": {
        # Tray icon
        "tray_open_test":   "Test-Oberfl\u00e4che \u00f6ffnen",
        "tray_settings":    "Einstellungen\u2026",
        "tray_quit":        "Beenden",
        "tray_starting":    "kodi-mpchc-bridge \u2014 wird gestartet\u2026",
        "tray_running":     "kodi-mpchc-bridge \u2014 l\u00e4uft  (Port {port})",
        "tray_stopped":     "kodi-mpchc-bridge \u2014 gestoppt  (Port {port})",

        # Settings dialog
        "settings_title":          "Einstellungen \u2014 Kodi-MPC-HC Bridge",
        "settings_kodi_section":   "Kodi-Verbindung",
        "settings_bridge_section": "Bridge-Server",
        "settings_host":           "Host",
        "settings_http_port":      "HTTP-Port",
        "settings_ws_port":        "WebSocket-Port",
        "settings_username":       "Benutzername",
        "settings_password":       "Passwort",
        "settings_mpchc_port":     "MPC-HC Port",
        "settings_bridge_port":    "Bridge-Port",
        "settings_auth_hint":      "Benutzername/Passwort leer lassen, wenn Kodi keine Authentifizierung verwendet.",
        "btn_save":                "\U0001f4be  Speichern",
        "btn_cancel":              "Abbrechen",
        "saved_title":             "Gespeichert",
        "saved_msg":               (
            "Einstellungen gespeichert.\n"
            "Bridge neu starten (Beenden \u2192 erneut \u00f6ffnen), "
            "damit die neuen Werte aktiv werden."
        ),
        "err_title":               "Fehler",
        "err_no_config":           "Config-Manager nicht verf\u00fcgbar.",
        "err_invalid_input":       "Ung\u00fcltige Eingabe",
        "err_int_expected":        "{key}: Ganzzahl erwartet.",
        "err_test_client":         "Test-Oberfl\u00e4che konnte nicht gestartet werden:\n{exc}",

        # Test client
        "tc_window_title":   "kodi-mpchc-bridge  \u2014  Test Client",
        "tc_now_playing":    " Aktuell ",
        "tc_playback":       " Wiedergabe ",
        "tc_volume_panel":   " Lautst\u00e4rke ",
        "tc_tracks_panel":   " Spuren ",
        "tc_nav_panel":      " Navigation ",
        "tc_state_lbl":      "Status",
        "tc_title_lbl":      "Titel",
        "tc_artist_lbl":     "Interpret",
        "tc_album_lbl":      "Album",
        "tc_type_lbl":       "Typ",
        "tc_pos_lbl":        "Position",
        "tc_dur_lbl":        "Dauer",
        "tc_vol_lbl":        "Lautst\u00e4rke",
        "tc_muted_lbl":      "Stumm",
        "tc_shuffle_lbl":    "Shuffle",
        "tc_repeat_lbl":     "Wiederholen",
        "tc_cover_lbl":      "Cover",
        "tc_seek_lbl":       "Springe zu (s)",
        "tc_audio_lbl":      "Audio",
        "tc_sub_lbl":        "Untertitel",
        "tc_chapter_lbl":    "Kapitel",
        "tc_log_lbl":        "Log",
        "tc_connected":      "\u25cf Verbunden",
        "tc_disconnected":   "\u25cf Getrennt",
        "tc_bridge_lbl":     "Bridge:",
        "tc_pillow_missing": "(Pillow nicht installiert)",
        "tc_off":            "Aus",

        # MPC Proxy settings
        "settings_proxy_section":   "MPC Proxy (Optional)",
        "settings_proxy_enabled":   "MPC Proxy aktivieren",
        "settings_proxy_path":      "Proxy-Programm",
        "btn_browse":               "Durchsuchen\u2026",
        "settings_proxy_setup_btn": "Kodi-Player einrichten",
        "settings_proxy_setup_ok":  "playercorefactory.xml wurde geschrieben nach:\n{path}",
        "settings_proxy_setup_err": "Einrichtung fehlgeschlagen:\n{err}",
        "settings_proxy_no_path":   "Bitte zuerst den Pfad zur MPC-Proxy-Exe angeben.",
    },

    # ── French ────────────────────────────────────────────────────────────────
    "fr": {
        # Tray icon
        "tray_open_test":   "Ouvrir l\u2019interface de test",
        "tray_settings":    "Param\u00e8tres\u2026",
        "tray_quit":        "Quitter",
        "tray_starting":    "kodi-mpchc-bridge \u2014 d\u00e9marrage\u2026",
        "tray_running":     "kodi-mpchc-bridge \u2014 actif  (port {port})",
        "tray_stopped":     "kodi-mpchc-bridge \u2014 arr\u00eat\u00e9  (port {port})",

        # Settings dialog
        "settings_title":          "Param\u00e8tres \u2014 Kodi-MPC-HC Bridge",
        "settings_kodi_section":   "Connexion Kodi",
        "settings_bridge_section": "Serveur Bridge",
        "settings_host":           "H\u00f4te",
        "settings_http_port":      "Port HTTP",
        "settings_ws_port":        "Port WebSocket",
        "settings_username":       "Nom d\u2019utilisateur",
        "settings_password":       "Mot de passe",
        "settings_mpchc_port":     "Port MPC-HC",
        "settings_bridge_port":    "Port Bridge",
        "settings_auth_hint":      "Laisser nom d\u2019utilisateur/mot de passe vides si Kodi n\u2019utilise pas d\u2019authentification.",
        "btn_save":                "\U0001f4be  Enregistrer",
        "btn_cancel":              "Annuler",
        "saved_title":             "Enregistr\u00e9",
        "saved_msg":               (
            "Param\u00e8tres enregistr\u00e9s.\n"
            "Red\u00e9marrez le bridge (Quitter \u2192 rouvrir) "
            "pour que les modifications prennent effet."
        ),
        "err_title":               "Erreur",
        "err_no_config":           "Gestionnaire de configuration non disponible.",
        "err_invalid_input":       "Entr\u00e9e invalide",
        "err_int_expected":        "{key}\u00a0: entier attendu.",
        "err_test_client":         "Impossible de lancer l\u2019interface de test\u00a0:\n{exc}",

        # Test client
        "tc_window_title":   "kodi-mpchc-bridge  \u2014  Client de test",
        "tc_now_playing":    " En cours ",
        "tc_playback":       " Lecture ",
        "tc_volume_panel":   " Volume ",
        "tc_tracks_panel":   " Pistes ",
        "tc_nav_panel":      " Navigation ",
        "tc_state_lbl":      "\u00c9tat",
        "tc_title_lbl":      "Titre",
        "tc_artist_lbl":     "Artiste",
        "tc_album_lbl":      "Album",
        "tc_type_lbl":       "Type",
        "tc_pos_lbl":        "Position",
        "tc_dur_lbl":        "Dur\u00e9e",
        "tc_vol_lbl":        "Volume",
        "tc_muted_lbl":      "Muet",
        "tc_shuffle_lbl":    "Al\u00e9atoire",
        "tc_repeat_lbl":     "R\u00e9p\u00e9ter",
        "tc_cover_lbl":      "Pochette",
        "tc_seek_lbl":       "Aller \u00e0 (s)",
        "tc_audio_lbl":      "Audio",
        "tc_sub_lbl":        "Sous-titres",
        "tc_chapter_lbl":    "Chapitre",
        "tc_log_lbl":        "Journal",
        "tc_connected":      "\u25cf Connect\u00e9",
        "tc_disconnected":   "\u25cf D\u00e9connect\u00e9",
        "tc_bridge_lbl":     "Bridge\u00a0:",
        "tc_pillow_missing": "(Pillow non install\u00e9)",
        "tc_off":            "D\u00e9sactiv\u00e9",

        # MPC Proxy settings
        "settings_proxy_section":   "MPC Proxy (Optionnel)",
        "settings_proxy_enabled":   "Activer MPC Proxy",
        "settings_proxy_path":      "Ex\u00e9cutable Proxy",
        "btn_browse":               "Parcourir\u2026",
        "settings_proxy_setup_btn": "Configurer Kodi Player",
        "settings_proxy_setup_ok":  "playercorefactory.xml \u00e9crit dans\u00a0:\n{path}",
        "settings_proxy_setup_err": "\u00c9chec de la configuration\u00a0:\n{err}",
        "settings_proxy_no_path":   "Veuillez d\u2019abord entrer le chemin de l\u2019ex\u00e9cutable MPC Proxy.",
    },

    # ── Spanish ───────────────────────────────────────────────────────────────
    "es": {
        # Tray icon
        "tray_open_test":   "Abrir interfaz de prueba",
        "tray_settings":    "Configuraci\u00f3n\u2026",
        "tray_quit":        "Salir",
        "tray_starting":    "kodi-mpchc-bridge \u2014 iniciando\u2026",
        "tray_running":     "kodi-mpchc-bridge \u2014 activo  (puerto {port})",
        "tray_stopped":     "kodi-mpchc-bridge \u2014 detenido  (puerto {port})",

        # Settings dialog
        "settings_title":          "Configuraci\u00f3n \u2014 Kodi-MPC-HC Bridge",
        "settings_kodi_section":   "Conexi\u00f3n Kodi",
        "settings_bridge_section": "Servidor Bridge",
        "settings_host":           "Host",
        "settings_http_port":      "Puerto HTTP",
        "settings_ws_port":        "Puerto WebSocket",
        "settings_username":       "Usuario",
        "settings_password":       "Contrase\u00f1a",
        "settings_mpchc_port":     "Puerto MPC-HC",
        "settings_bridge_port":    "Puerto Bridge",
        "settings_auth_hint":      "Dejar usuario/contrase\u00f1a vac\u00edos si Kodi no requiere autenticaci\u00f3n.",
        "btn_save":                "\U0001f4be  Guardar",
        "btn_cancel":              "Cancelar",
        "saved_title":             "Guardado",
        "saved_msg":               (
            "Configuraci\u00f3n guardada.\n"
            "Reinicie el bridge (Salir \u2192 volver a abrir) "
            "para que los cambios surtan efecto."
        ),
        "err_title":               "Error",
        "err_no_config":           "Gestor de configuraci\u00f3n no disponible.",
        "err_invalid_input":       "Entrada no v\u00e1lida",
        "err_int_expected":        "{key}: se esperaba un entero.",
        "err_test_client":         "No se pudo iniciar la interfaz de prueba:\n{exc}",

        # Test client
        "tc_window_title":   "kodi-mpchc-bridge  \u2014  Cliente de prueba",
        "tc_now_playing":    " Reproduciendo ",
        "tc_playback":       " Reproducci\u00f3n ",
        "tc_volume_panel":   " Volumen ",
        "tc_tracks_panel":   " Pistas ",
        "tc_nav_panel":      " Navegaci\u00f3n ",
        "tc_state_lbl":      "Estado",
        "tc_title_lbl":      "T\u00edtulo",
        "tc_artist_lbl":     "Artista",
        "tc_album_lbl":      "\u00c1lbum",
        "tc_type_lbl":       "Tipo",
        "tc_pos_lbl":        "Posici\u00f3n",
        "tc_dur_lbl":        "Duraci\u00f3n",
        "tc_vol_lbl":        "Volumen",
        "tc_muted_lbl":      "Silencio",
        "tc_shuffle_lbl":    "Aleatorio",
        "tc_repeat_lbl":     "Repetir",
        "tc_cover_lbl":      "Portada",
        "tc_seek_lbl":       "Ir a (s)",
        "tc_audio_lbl":      "Audio",
        "tc_sub_lbl":        "Subt\u00edtulos",
        "tc_chapter_lbl":    "Cap\u00edtulo",
        "tc_log_lbl":        "Registro",
        "tc_connected":      "\u25cf Conectado",
        "tc_disconnected":   "\u25cf Desconectado",
        "tc_bridge_lbl":     "Bridge:",
        "tc_pillow_missing": "(Pillow no instalado)",
        "tc_off":            "Desactivado",

        # MPC Proxy settings
        "settings_proxy_section":   "MPC Proxy (Opcional)",
        "settings_proxy_enabled":   "Habilitar MPC Proxy",
        "settings_proxy_path":      "Ejecutable Proxy",
        "btn_browse":               "Examinar\u2026",
        "settings_proxy_setup_btn": "Configurar Kodi Player",
        "settings_proxy_setup_ok":  "playercorefactory.xml escrito en:\n{path}",
        "settings_proxy_setup_err": "Error en la configuraci\u00f3n:\n{err}",
        "settings_proxy_no_path":   "Por favor, indique primero la ruta al ejecutable MPC Proxy.",
    },

    # ── Italian ───────────────────────────────────────────────────────────────
    "it": {
        # Tray icon
        "tray_open_test":   "Apri interfaccia di test",
        "tray_settings":    "Impostazioni\u2026",
        "tray_quit":        "Esci",
        "tray_starting":    "kodi-mpchc-bridge \u2014 avvio\u2026",
        "tray_running":     "kodi-mpchc-bridge \u2014 attivo  (porta {port})",
        "tray_stopped":     "kodi-mpchc-bridge \u2014 fermo  (porta {port})",

        # Settings dialog
        "settings_title":          "Impostazioni \u2014 Kodi-MPC-HC Bridge",
        "settings_kodi_section":   "Connessione Kodi",
        "settings_bridge_section": "Server Bridge",
        "settings_host":           "Host",
        "settings_http_port":      "Porta HTTP",
        "settings_ws_port":        "Porta WebSocket",
        "settings_username":       "Utente",
        "settings_password":       "Password",
        "settings_mpchc_port":     "Porta MPC-HC",
        "settings_bridge_port":    "Porta Bridge",
        "settings_auth_hint":      "Lasciare utente/password vuoti se Kodi non richiede autenticazione.",
        "btn_save":                "\U0001f4be  Salva",
        "btn_cancel":              "Annulla",
        "saved_title":             "Salvato",
        "saved_msg":               (
            "Impostazioni salvate.\n"
            "Riavviare il bridge (Esci \u2192 riaprire) "
            "per applicare le modifiche."
        ),
        "err_title":               "Errore",
        "err_no_config":           "Gestore configurazione non disponibile.",
        "err_invalid_input":       "Input non valido",
        "err_int_expected":        "{key}: atteso un intero.",
        "err_test_client":         "Impossibile avviare l\u2019interfaccia di test:\n{exc}",

        # Test client
        "tc_window_title":   "kodi-mpchc-bridge  \u2014  Client di test",
        "tc_now_playing":    " In riproduzione ",
        "tc_playback":       " Riproduzione ",
        "tc_volume_panel":   " Volume ",
        "tc_tracks_panel":   " Tracce ",
        "tc_nav_panel":      " Navigazione ",
        "tc_state_lbl":      "Stato",
        "tc_title_lbl":      "Titolo",
        "tc_artist_lbl":     "Artista",
        "tc_album_lbl":      "Album",
        "tc_type_lbl":       "Tipo",
        "tc_pos_lbl":        "Posizione",
        "tc_dur_lbl":        "Durata",
        "tc_vol_lbl":        "Volume",
        "tc_muted_lbl":      "Muto",
        "tc_shuffle_lbl":    "Casuale",
        "tc_repeat_lbl":     "Ripeti",
        "tc_cover_lbl":      "Copertina",
        "tc_seek_lbl":       "Vai a (s)",
        "tc_audio_lbl":      "Audio",
        "tc_sub_lbl":        "Sottotitoli",
        "tc_chapter_lbl":    "Capitolo",
        "tc_log_lbl":        "Log",
        "tc_connected":      "\u25cf Connesso",
        "tc_disconnected":   "\u25cf Disconnesso",
        "tc_bridge_lbl":     "Bridge:",
        "tc_pillow_missing": "(Pillow non installato)",
        "tc_off":            "Disattivato",

        # MPC Proxy settings
        "settings_proxy_section":   "MPC Proxy (Opzionale)",
        "settings_proxy_enabled":   "Abilita MPC Proxy",
        "settings_proxy_path":      "Eseguibile Proxy",
        "btn_browse":               "Sfoglia\u2026",
        "settings_proxy_setup_btn": "Configura Kodi Player",
        "settings_proxy_setup_ok":  "playercorefactory.xml scritto in:\n{path}",
        "settings_proxy_setup_err": "Configurazione fallita:\n{err}",
        "settings_proxy_no_path":   "Indicare prima il percorso dell\u2019eseguibile MPC Proxy.",
    },
}

_SUPPORTED: frozenset[str] = frozenset(_STRINGS.keys())
_ACTIVE_LANG: str = LANG if LANG in _SUPPORTED else "en"

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def T(key: str, **kwargs: object) -> str:
    """
    Return the translated string for *key* in the active language.

    Falls back to English if the key is missing in the active language.
    Keyword arguments are substituted via str.format(**kwargs).

    Example::

        T("tray_running", port=13590)
    """
    s: str = (
        _STRINGS.get(_ACTIVE_LANG, {}).get(key)
        or _STRINGS["en"].get(key)
        or key
    )
    if kwargs:
        try:
            s = s.format(**kwargs)
        except Exception:
            pass
    return s
