# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Le Sanglier des Ardennes
"""Tests de install.py."""

import os
import re
import unittest
from pathlib import Path
from unittest import mock

import install


def parse_exec_arg(value):
    """Décode un argument Exec entre guillemets (chaîne, %%, puis guillemets)."""
    value = value.replace("\\\\", "\\").replace("%%", "%")
    assert value.startswith('"') and value.endswith('"'), value
    return re.sub(r'\\(["`$\\])', r"\1", value[1:-1])


class QuoteExecArgTest(unittest.TestCase):
    def test_chemin_simple(self):
        self.assertEqual(install.quote_exec_arg("/a/b.py"), '"/a/b.py"')

    def test_espaces(self):
        self.assertEqual(install.quote_exec_arg("/mes jeux/b.py"), '"/mes jeux/b.py"')

    def test_caracteres_reserves(self):
        # Après l'échappement de chaîne puis de guillemets, \ s'écrit sur 4 caractères
        self.assertEqual(install.quote_exec_arg('/a"b$c`d%e\\f'),
                         '"/a\\\\"b\\\\$c\\\\`d%%e\\\\\\\\f"')

    def test_relecture(self):
        path = '/dossier "spécial"/$HOME/`id`/50%/a\\b.py'
        self.assertEqual(parse_exec_arg(install.quote_exec_arg(path)), path)


class DesktopEntryTest(unittest.TestCase):
    def test_chemins_adaptes(self):
        project = Path("/mes jeux/NetHack Launcher")
        with mock.patch.object(install, "PROJECT_DIR", project), \
                mock.patch.object(install, "LAUNCHER", project / "nethack_launcher.py"):
            entry = install.desktop_entry()
        lines = entry.splitlines()
        self.assertIn('Exec="/mes jeux/NetHack Launcher/nethack_launcher.py"', lines)
        self.assertIn("Path=/mes jeux/NetHack Launcher", lines)
        self.assertIn(f"Icon={install.APP_ID}", lines)
        self.assertIn("Terminal=true", lines)
        self.assertNotIn("@", entry)  # aucun marqueur du modèle ne doit subsister
        self.assertFalse(any(line.startswith("#") for line in lines))


class IsLubuntuTest(unittest.TestCase):
    def check(self, os_release, session="", lubuntu_dir=False):
        env = {"DESKTOP_SESSION": session, "XDG_SESSION_DESKTOP": ""}
        with mock.patch.object(install, "read_os_release", return_value=os_release), \
                mock.patch.dict(os.environ, env), \
                mock.patch.object(Path, "is_dir", return_value=lubuntu_dir):
            return install.is_lubuntu()

    def test_session_lubuntu(self):
        self.assertTrue(self.check({"ID": "ubuntu"}, session="Lubuntu"))

    def test_paquet_lubuntu(self):
        self.assertTrue(self.check({"ID": "ubuntu"}, lubuntu_dir=True))

    def test_derivee_ubuntu(self):
        self.assertTrue(self.check({"ID": "pop", "ID_LIKE": "ubuntu debian"}, session="lubuntu"))

    def test_ubuntu_sans_lubuntu(self):
        self.assertFalse(self.check({"ID": "ubuntu"}, session="ubuntu"))

    def test_autre_distribution(self):
        self.assertFalse(self.check({"ID": "fedora"}, session="Lubuntu", lubuntu_dir=True))


if __name__ == "__main__":
    unittest.main()
