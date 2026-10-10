# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Le Sanglier des Ardennes
"""Tests de nethack_launcher.py (fonctions sans interface curses)."""

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import nethack_launcher as nl


def make_executable(path, content="#!/bin/sh\n"):
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


class SplitArgsTest(unittest.TestCase):
    def test_sans_option(self):
        self.assertEqual(nl.split_args(["-u", "Bob"]), (None, ["-u", "Bob"]))

    def test_option_separee(self):
        self.assertEqual(nl.split_args(["-u", "Bob", "--nethack", "/x"]), ("/x", ["-u", "Bob"]))

    def test_option_avec_egal(self):
        self.assertEqual(nl.split_args(["--nethack=~/y", "-D"]), ("~/y", ["-D"]))

    def test_option_sans_valeur(self):
        with self.assertRaises(SystemExit):
            nl.split_args(["--nethack"])

    def test_aide(self):
        for flag in ("-h", "--help"):
            with mock.patch("builtins.print") as fake_print, self.assertRaises(SystemExit) as ctx:
                nl.split_args(["-u", "Bob", flag])
            self.assertEqual(ctx.exception.code, 0)
            self.assertIn("--nethack", fake_print.call_args.args[0])


class FindNethackTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.game = make_executable(self.dir / "nethack")
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        os.environ.pop("NETHACK", None)
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)

    def test_option_prioritaire_sur_variable(self):
        os.environ["NETHACK"] = "/introuvable"
        self.assertEqual(nl.find_nethack(str(self.game)), (str(self.game), None))

    def test_variable_environnement(self):
        os.environ["NETHACK"] = str(self.game)
        self.assertEqual(nl.find_nethack(None), (str(self.game), None))

    def test_chemin_explicite_invalide_sans_repli(self):
        with mock.patch.object(nl, "NETHACK_CANDIDATES", [str(self.game)]):
            path, error = nl.find_nethack("/introuvable")
        self.assertIsNone(path)
        self.assertIn("--nethack", error)

    def test_emplacements_connus(self):
        with mock.patch.object(nl, "NETHACK_CANDIDATES", [None, "/introuvable", str(self.game)]):
            self.assertEqual(nl.find_nethack(None), (str(self.game), None))

    def test_introuvable(self):
        with mock.patch.object(nl, "NETHACK_CANDIDATES", [None, "/introuvable"]):
            path, error = nl.find_nethack(None)
        self.assertIsNone(path)
        self.assertIn("NETHACK", error)

    def test_fichier_non_executable(self):
        plain = self.dir / "texte"
        plain.write_text("")
        self.assertIsNone(nl.find_nethack(str(plain))[0])


class DetectionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def fake_binary(self, *libraries):
        binary = self.dir / "lib" / "nethack"
        binary.parent.mkdir(exist_ok=True)
        binary.write_bytes(b"\x7fELF" + b"\0".join(lib + b".so.6" for lib in libraries))
        return binary

    def wrapper(self, body):
        return make_executable(self.dir / "nethack", "#!/bin/sh\n" + body)

    def test_resolve_script_installe(self):
        script = self.wrapper(f"HACKDIR={self.dir}/lib\nHACK=$HACKDIR/nethack\n")
        self.assertEqual(nl.resolve_binary(str(script)), f"{self.dir}/lib/nethack")

    def test_resolve_hack_par_defaut(self):
        script = self.wrapper(f"HACKDIR={self.dir}/lib\n")
        self.assertEqual(nl.resolve_binary(str(script)), f"{self.dir}/lib/nethack")

    def test_resolve_binaire_direct(self):
        binary = self.fake_binary()
        self.assertEqual(nl.resolve_binary(str(binary)), str(binary))

    def test_resolve_script_inconnu(self):
        self.assertIsNone(nl.resolve_binary(str(self.wrapper("exec /usr/bin/true\n"))))

    def test_toutes_interfaces(self):
        binary = self.fake_binary(b"libncursesw", b"libXaw", b"libQt6Widgets")
        self.assertEqual(nl.detect_unsupported(str(binary)), set())

    def test_interfaces_manquantes(self):
        binary = self.fake_binary(b"libncursesw")
        self.assertEqual(nl.detect_unsupported(str(binary)), {"X11", "Qt"})

    def test_via_script(self):
        self.fake_binary(b"libXaw")
        script = self.wrapper(f"HACKDIR={self.dir}/lib\n")
        self.assertEqual(nl.detect_unsupported(str(script)), {"Curses", "Qt"})

    def test_doute_tout_propose(self):
        static = self.dir / "statique"
        static.write_bytes(b"\x7fELF sans bibliotheque")
        self.assertEqual(nl.detect_unsupported(str(static)), set())
        self.assertEqual(nl.detect_unsupported("/introuvable"), set())


class UnavailableReasonTest(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        for var in ("DISPLAY", "WAYLAND_DISPLAY"):
            os.environ.pop(var, None)
        self.modes = {mode.label: mode for mode in nl.MODES}

    def reasons(self):
        return {label: nl.unavailable_reason(mode) for label, mode in self.modes.items()}

    def test_sans_affichage(self):
        reasons = self.reasons()
        self.assertIsNone(reasons["Terminal"])
        self.assertIsNone(reasons["Curses"])
        self.assertEqual(reasons["X11"], "pas de serveur X")
        self.assertEqual(reasons["Qt"], "pas d'affichage graphique")

    def test_wayland_seul(self):
        os.environ["WAYLAND_DISPLAY"] = "wayland-0"
        reasons = self.reasons()
        self.assertEqual(reasons["X11"], "pas de serveur X")
        self.assertIsNone(reasons["Qt"])

    def test_serveur_x(self):
        os.environ["DISPLAY"] = ":0"
        self.assertTrue(all(reason is None for reason in self.reasons().values()))

    def test_non_compile(self):
        os.environ["DISPLAY"] = ":0"
        with mock.patch.object(nl, "UNSUPPORTED", {"Qt"}):
            self.assertEqual(self.reasons()["Qt"], "non compilé dans NetHack")


class LastModeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        config_dir = os.path.join(self.tmp.name, "nethack-launcher")
        for name, value in (("CONFIG_DIR", config_dir),
                            ("LAST_MODE_FILE", os.path.join(config_dir, "last_mode"))):
            patcher = mock.patch.object(nl, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_par_defaut(self):
        self.assertEqual(nl.load_last_mode(), 0)

    def test_aller_retour(self):
        nl.save_last_mode(nl.MODES[2])
        self.assertEqual(nl.load_last_mode(), 2)

    def test_mode_inconnu(self):
        os.makedirs(nl.CONFIG_DIR)
        with open(nl.LAST_MODE_FILE, "w") as f:
            f.write("Supprimé\n")
        self.assertEqual(nl.load_last_mode(), 0)


if __name__ == "__main__":
    unittest.main()
