#!/usr/bin/env python3
"""Lanceur TUI pour NetHack : choix du mode graphique (Terminal, Curses, X11, Qt)."""

import curses
import os
import shutil
import subprocess
import sys

NETHACK = "/home/util01/nh/install/games/nethack"

# (libellé, description, options passées à nethack, nécessite un serveur X)
MODES = [
    ("Terminal", "Interface texte classique (tty)", ["-wtty"], False),
    ("Curses", "Interface texte curses (fenêtres)", ["-wcurses"], False),
    ("X11", "Interface graphique X11 (tuiles)", ["-wX11"], True),
    ("Qt", "Interface graphique Qt", ["-wQT"], True),
]

TITLE = [
    r" _   _      _   _   _            _    ",
    r"| \ | | ___| |_| | | | __ _  ___| | __",
    r"|  \| |/ _ \ __| |_| |/ _` |/ __| |/ /",
    r"| |\  |  __/ |_|  _  | (_| | (__|   < ",
    r"|_| \_|\___|\__|_| |_|\__,_|\___|_|\_\ ",
]


def has_display():
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def available(mode):
    return not mode[3] or has_display()


def addstr_center(win, y, text, attr=0):
    h, w = win.getmaxyx()
    if 0 <= y < h:
        x = max(0, (w - len(text)) // 2)
        win.addnstr(y, x, text, max(0, w - x - 1), attr)


def draw(stdscr, selected, message):
    stdscr.erase()
    h, w = stdscr.getmaxyx()
    y = 1
    if h >= len(TITLE) + len(MODES) + 10 and w > 42:
        for line in TITLE:
            addstr_center(stdscr, y, line, curses.color_pair(1) | curses.A_BOLD)
            y += 1
    else:
        addstr_center(stdscr, y, "NetHack", curses.color_pair(1) | curses.A_BOLD)
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
            attr = curses.color_pair(2) | curses.A_BOLD
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
        addstr_center(stdscr, y + 2, message, curses.color_pair(3) | curses.A_BOLD)
    stdscr.refresh()


def run_nethack(stdscr, mode, extra_args):
    label, _, args, graphical = mode
    cmd = [NETHACK, *args, *extra_args]
    curses.def_prog_mode()
    curses.endwin()
    if graphical:
        print(f"NetHack ({label}) est lancé dans une fenêtre séparée...")
    try:
        rc = subprocess.call(cmd)
    except OSError as exc:
        rc = None
        err = str(exc)
    finally:
        curses.reset_prog_mode()
        stdscr.clear()
        curses.curs_set(0)
    if rc is None:
        return f"Erreur : {err}"
    if rc != 0:
        return f"NetHack ({label}) s'est terminé avec le code {rc}"
    return f"Partie en mode {label} terminée."


def main(stdscr, extra_args):
    curses.curs_set(0)
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_YELLOW, -1)
    curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(3, curses.COLOR_RED, -1)
    stdscr.keypad(True)

    selected = 0
    message = ""
    while True:
        draw(stdscr, selected, message)
        key = stdscr.getch()
        message = ""
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
                message = f"Le mode {mode[0]} nécessite un affichage graphique (DISPLAY)."
                continue
            message = run_nethack(stdscr, mode, extra_args)


if __name__ == "__main__":
    if not (os.path.isfile(NETHACK) and os.access(NETHACK, os.X_OK)):
        sys.exit(f"Exécutable NetHack introuvable : {NETHACK}")
    if not sys.stdin.isatty() or shutil.get_terminal_size().columns == 0:
        sys.exit("Ce lanceur doit être exécuté dans un terminal.")
    os.environ.setdefault("ESCDELAY", "25")
    # Les arguments supplémentaires sont transmis à nethack (ex. : -u NomDuJoueur)
    curses.wrapper(main, sys.argv[1:])
