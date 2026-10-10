#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Le Sanglier des Ardennes
"""Lanceur TUI pour NetHack : choix du mode graphique (Terminal, Curses, X11, Qt)."""

import curses
import os
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

# (libellé, description, options passées à nethack, nécessite un serveur X)
MODES = [
    ("Terminal", "Interface texte classique (tty)", ["-wtty"], False),
    ("Curses", "Interface texte curses (fenêtres)", ["-wcurses"], False),
    ("X11", "Interface graphique X11 (tuiles)", ["-wX11"], True),
    ("Qt", "Interface graphique Qt", ["-wQT"], True),
]

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


def has_display():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def available(mode):
    return not mode[3] or has_display()


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
        ok = available(mode)
        text = f" {i + 1}. {label:<9} {desc}"
        if not ok:
            text = f" {i + 1}. {label:<9} (pas d'affichage graphique)"
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
            if not available(mode):
                message, error = f"Le mode {mode[0]} nécessite un affichage graphique (DISPLAY).", True
                continue
            save_last_mode(mode)
            message, error = run_nethack(stdscr, nethack, mode, extra_args)


if __name__ == "__main__":
    # Les autres arguments sont transmis à nethack (ex. : -u NomDuJoueur)
    cli_path, extra_args = split_args(sys.argv[1:])
    nethack, error = find_nethack(cli_path)
    if error:
        sys.exit(error)
    if not sys.stdin.isatty() or shutil.get_terminal_size().columns == 0:
        sys.exit("Ce lanceur doit être exécuté dans un terminal.")
    os.environ.setdefault("ESCDELAY", "25")
    curses.wrapper(main, nethack, extra_args)
