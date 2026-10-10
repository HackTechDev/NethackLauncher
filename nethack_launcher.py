#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Le Sanglier des Ardennes
"""Lanceur TUI pour NetHack : choix du mode graphique (Terminal, Curses, X11, Qt)."""

import curses
import os
import re
import shutil
import subprocess
import sys

# Emplacements essayés, dans l'ordre, si ni --nethack ni $NETHACK ne sont fournis
# (~/nh/install est le préfixe d'installation par défaut des sources de NetHack)
NETHACK_CANDIDATES = [
    shutil.which("nethack"),
    os.path.expanduser("~/nh/install/games/nethack"),
    "/usr/games/nethack",
]

# (libellé, description, options passées à nethack,
#  variables d'affichage dont l'une doit être définie ; vide pour un mode texte)
MODES = [
    ("Terminal", "Interface texte classique (tty)", ["-wtty"], ()),
    ("Curses", "Interface texte curses (fenêtres)", ["-wcurses"], ()),
    ("X11", "Interface graphique X11 (tuiles)", ["-wX11"], ("DISPLAY",)),
    ("Qt", "Interface graphique Qt", ["-wQT"], ("DISPLAY", "WAYLAND_DISPLAY")),
]

# Bibliothèque dont dépend chaque interface : si le binaire ne la référence pas,
# l'interface n'a pas été compilée (tty, toujours présente, n'en a pas besoin)
PORT_LIBRARIES = {"Curses": b"libncurses", "X11": b"libXaw", "Qt": b"libQt"}

CONFIG_DIR = os.path.join(os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config"),
                          "nethack-launcher")
LAST_MODE_FILE = os.path.join(CONFIG_DIR, "last_mode")

TITLE = [
    r" _   _      _   _   _            _    ",
    r"| \ | | ___| |_| | | | __ _  ___| | __",
    r"|  \| |/ _ \ __| |_| |/ _` |/ __| |/ /",
    r"| |\  |  __/ |_|  _  | (_| | (__|   < ",
    r"|_| \_|\___|\__|_| |_|\__,_|\___|_|\_\ ",
]


# Paires de couleurs ; restent à False sur un terminal sans couleurs
COLORS = False


def init_colors():
    global COLORS
    if not curses.has_colors():
        return
    try:
        curses.use_default_colors()
        background = -1
    except curses.error:
        background = curses.COLOR_BLACK
    curses.init_pair(1, curses.COLOR_YELLOW, background)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(3, curses.COLOR_RED, background)
    curses.init_pair(4, curses.COLOR_GREEN, background)
    COLORS = True


def color(pair, fallback=curses.A_NORMAL):
    """Attribut de la paire de couleurs, ou `fallback` en monochrome."""
    return curses.color_pair(pair) if COLORS else fallback


def hide_cursor():
    try:
        curses.curs_set(0)
    except curses.error:
        pass  # terminal incapable de masquer le curseur (ex. : vt100)


def load_last_mode():
    """Index du dernier mode lancé, ou 0 s'il est inconnu."""
    try:
        with open(LAST_MODE_FILE, encoding="utf-8") as f:
            label = f.read().strip()
    except OSError:
        return 0
    return next((i for i, mode in enumerate(MODES) if mode[0] == label), 0)


def save_last_mode(mode):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(LAST_MODE_FILE, "w", encoding="utf-8") as f:
            f.write(mode[0] + "\n")
    except OSError:
        pass  # mémoriser le mode est un confort, pas une nécessité


def resolve_binary(nethack):
    """Chemin du vrai binaire : suit le script nethack installé (HACKDIR/HACK)."""
    try:
        with open(nethack, "rb") as f:
            if f.read(2) != b"#!":
                return nethack
        with open(nethack, encoding="utf-8", errors="replace") as f:
            script = f.read()
    except OSError:
        return None
    hackdir = re.search(r"^HACKDIR=(\S+)", script, re.M)
    hack = re.search(r"^HACK=(\S+)", script, re.M)
    if not hackdir:
        return None
    binary = hack.group(1) if hack else "$HACKDIR/nethack"
    return binary.replace("$HACKDIR", hackdir.group(1)).replace("${HACKDIR}", hackdir.group(1))


def detect_unsupported(nethack):
    """Libellés des modes absents du binaire ; ensemble vide en cas de doute."""
    binary = resolve_binary(nethack)
    try:
        with open(binary, "rb") as f:
            data = f.read()
    except (OSError, TypeError):
        return set()
    if not data.startswith(b"\x7fELF") or b".so" not in data:
        return set()  # binaire statique ou inconnu : impossible de conclure
    return {label for label, lib in PORT_LIBRARIES.items() if lib not in data}


# Modes que le binaire NetHack ne prend pas en charge (rempli au démarrage)
UNSUPPORTED = set()


def unavailable_reason(mode):
    """Raison pour laquelle le mode ne peut pas être lancé, ou None."""
    if mode[0] in UNSUPPORTED:
        return "non compilé dans NetHack"
    displays = mode[3]
    if displays and not any(os.environ.get(var) for var in displays):
        return "pas de serveur X" if displays == ("DISPLAY",) else "pas d'affichage graphique"
    return None


def addstr_center(win, y, text, attr=0):
    h, w = win.getmaxyx()
    if 0 <= y < h:
        x = max(0, (w - len(text)) // 2)
        win.addnstr(y, x, text, max(0, w - x - 1), attr)


def draw(stdscr, selected, message, error):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    y = 1
    if h >= len(TITLE) + len(MODES) + 10 and w > 42:
        for line in TITLE:
            addstr_center(stdscr, y, line, color(1) | curses.A_BOLD)
            y += 1
    else:
        addstr_center(stdscr, y, "NetHack", color(1) | curses.A_BOLD)
        y += 1
    y += 1
    addstr_center(stdscr, y, "Choisissez un mode d'affichage", curses.A_BOLD)
    y += 2

    width = 44
    for i, mode in enumerate(MODES):
        label, desc, _, _ = mode
        reason = unavailable_reason(mode)
        ok = reason is None
        text = f" {i + 1}. {label:<9} {desc if ok else f'({reason})'}"
        text = text.ljust(width)[:width]
        if i == selected:
            attr = color(2, curses.A_REVERSE) | curses.A_BOLD
        elif not ok:
            attr = curses.A_DIM
        else:
            attr = curses.A_NORMAL
        addstr_center(stdscr, y, text, attr)
        y += 1

    y += 1
    addstr_center(stdscr, y, f"↑/↓ : naviguer   Entrée : lancer   1-{len(MODES)} : accès direct   q : quitter",
                  curses.A_DIM)
    if message:
        attr = color(3) | curses.A_BOLD if error else color(4)
        addstr_center(stdscr, y + 2, message, attr)
    stdscr.refresh()


def is_executable(path):
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def find_nethack(cli_path):
    """Retourne (chemin, erreur) : --nethack, puis $NETHACK, puis les emplacements connus."""
    for source, path in (("--nethack", cli_path), ("NETHACK", os.environ.get("NETHACK"))):
        if path:
            path = os.path.expanduser(path)
            if is_executable(path):
                return path, None
            return None, f"Exécutable NetHack introuvable ({source}) : {path}"
    for path in NETHACK_CANDIDATES:
        if is_executable(path):
            return path, None
    return None, ("Exécutable NetHack introuvable. Indiquez son chemin avec "
                  "--nethack CHEMIN ou la variable d'environnement NETHACK.")


def split_args(argv):
    """Sépare l'option --nethack des arguments transmis à nethack."""
    cli_path, extra = None, []
    it = iter(argv)
    for arg in it:
        if arg == "--nethack":
            cli_path = next(it, None)
            if cli_path is None:
                sys.exit("L'option --nethack attend un chemin.")
        elif arg.startswith("--nethack="):
            cli_path = arg.split("=", 1)[1]
        else:
            extra.append(arg)
    return cli_path, extra


def run_nethack(stdscr, nethack, mode, extra_args):
    label, _, args, graphical = mode
    cmd = [nethack, *args, *extra_args]
    curses.def_prog_mode()
    curses.endwin()
    if graphical:
        print(f"NetHack ({label}) est lancé dans une fenêtre séparée...")
    err = None
    try:
        rc = subprocess.call(cmd)
    except OSError as exc:
        rc = None
        err = str(exc)
    try:
        if rc != 0:
            # Laisse le temps de lire les messages de NetHack avant de redessiner le menu
            print(f"\nNetHack ({label}) a échoué : {err or f'code de sortie {rc}'}")
            try:
                input("Appuyez sur Entrée pour revenir au menu...")
            except EOFError:
                pass
    finally:
        curses.reset_prog_mode()
        stdscr.clear()
        hide_cursor()
    if rc is None:
        return f"Erreur : {err}", True
    if rc != 0:
        return f"NetHack ({label}) s'est terminé avec le code {rc}", True
    return f"Partie en mode {label} terminée.", False


def main(stdscr, nethack, extra_args):
    hide_cursor()
    init_colors()
    stdscr.keypad(True)

    selected = load_last_mode()
    message, error = "", False
    while True:
        draw(stdscr, selected, message, error)
        key = stdscr.getch()
        message, error = "", False
        if key in (curses.KEY_UP, ord("k")):
            selected = (selected - 1) % len(MODES)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = (selected + 1) % len(MODES)
        elif key in (ord("q"), ord("Q"), 27):
            return
        elif key == curses.KEY_RESIZE:
            continue
        elif key in (curses.KEY_ENTER, 10, 13) or ord("1") <= key < ord("1") + len(MODES):
            if key not in (curses.KEY_ENTER, 10, 13):
                selected = key - ord("1")
            mode = MODES[selected]
            reason = unavailable_reason(mode)
            if reason:
                message, error = f"Mode {mode[0]} indisponible : {reason}.", True
                continue
            save_last_mode(mode)
            message, error = run_nethack(stdscr, nethack, mode, extra_args)


if __name__ == "__main__":
    # Les autres arguments sont transmis à nethack (ex. : -u NomDuJoueur)
    cli_path, extra_args = split_args(sys.argv[1:])
    nethack, error = find_nethack(cli_path)
    if error:
        sys.exit(error)
    UNSUPPORTED = detect_unsupported(nethack)
    if not sys.stdin.isatty() or shutil.get_terminal_size().columns == 0:
        sys.exit("Ce lanceur doit être exécuté dans un terminal.")
    os.environ.setdefault("ESCDELAY", "25")
    curses.wrapper(main, nethack, extra_args)
