#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Le Sanglier des Ardennes
"""Installe (ou désinstalle) le raccourci et l'icône du lanceur NetHack.

Pour l'instant, seul Lubuntu est pris en charge.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

APP_ID = "nethack-launcher"
PROJECT_DIR = Path(__file__).resolve().parent
LAUNCHER = PROJECT_DIR / "nethack_launcher.py"
DESKTOP_SRC = PROJECT_DIR / f"{APP_ID}.desktop.in"
ICON_SRC = PROJECT_DIR / f"{APP_ID}.svg"

DATA_HOME = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
APPS_DIR = DATA_HOME / "applications"
ICON_THEME_DIR = DATA_HOME / "icons/hicolor"
DESKTOP_DST = APPS_DIR / f"{APP_ID}.desktop"
ICON_DST = ICON_THEME_DIR / "scalable/apps" / f"{APP_ID}.svg"


def read_os_release():
    info = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.strip().partition("=")
                if sep:
                    info[key] = value.strip('"')
    except OSError:
        pass
    return info


def is_lubuntu():
    info = read_os_release()
    if "ubuntu" not in (info.get("ID", "") + " " + info.get("ID_LIKE", "")).lower():
        return False
    session = " ".join(os.environ.get(v, "") for v in ("DESKTOP_SESSION", "XDG_SESSION_DESKTOP"))
    return "lubuntu" in session.lower() or Path("/usr/share/lubuntu").is_dir()


def escape_string(value):
    """Échappement d'une valeur de type chaîne (spécification Desktop Entry)."""
    return (value.replace("\\", "\\\\").replace("\n", "\\n")
            .replace("\t", "\\t").replace("\r", "\\r"))


def quote_exec_arg(arg):
    """Argument de la clé Exec, entre guillemets et échappé selon la spécification."""
    for char in '\\"`$':
        arg = arg.replace(char, "\\" + char)
    return escape_string(f'"{arg}"'.replace("%", "%%"))


def desktop_entry():
    """Contenu du raccourci, généré depuis le modèle avec les chemins du projet."""
    lines = []
    for line in DESKTOP_SRC.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue  # commentaires propres au modèle
        if line.startswith("Exec="):
            line = f"Exec={quote_exec_arg(str(LAUNCHER))}"
        elif line.startswith("Path="):
            line = f"Path={escape_string(str(PROJECT_DIR))}"
        elif line.startswith("Icon="):
            line = f"Icon={APP_ID}"
        lines.append(line)
    return "\n".join(lines) + "\n"


def refresh_caches():
    """Met à jour les caches du menu et des icônes (sans échec si l'outil est absent)."""
    for cmd in (["update-desktop-database", str(APPS_DIR)],
                ["gtk-update-icon-cache", "-f", "-t", str(ICON_THEME_DIR)]):
        if shutil.which(cmd[0]):
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def install():
    for path in (LAUNCHER, DESKTOP_SRC, ICON_SRC):
        if not path.is_file():
            sys.exit(f"Fichier introuvable : {path}")
    LAUNCHER.chmod(LAUNCHER.stat().st_mode | 0o111)

    ICON_DST.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ICON_SRC, ICON_DST)
    print(f"Icône installée     : {ICON_DST}")

    APPS_DIR.mkdir(parents=True, exist_ok=True)
    DESKTOP_DST.write_text(desktop_entry(), encoding="utf-8")
    DESKTOP_DST.chmod(0o644)
    print(f"Raccourci installé  : {DESKTOP_DST}")

    refresh_caches()
    print("\n« NetHack Launcher » est disponible dans le menu Jeux.")
    print("S'il n'apparaît pas tout de suite, fermez puis rouvrez votre session.")


def uninstall():
    for path in (DESKTOP_DST, ICON_DST):
        if path.exists():
            path.unlink()
            print(f"Supprimé : {path}")
        else:
            print(f"Absent   : {path}")
    refresh_caches()


def main():
    parser = argparse.ArgumentParser(
        description="Installe le raccourci et l'icône du lanceur NetHack.")
    parser.add_argument("-u", "--uninstall", action="store_true",
                        help="supprime le raccourci et l'icône")
    args = parser.parse_args()

    if not is_lubuntu():
        print("Attention : ce script ne prend en charge que Lubuntu pour l'instant.\n"
              "Aucune modification n'a été effectuée.", file=sys.stderr)
        sys.exit(1)

    uninstall() if args.uninstall else install()


if __name__ == "__main__":
    main()
