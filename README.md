# NetHack Launcher

Lanceur en mode terminal (TUI) pour NetHack, permettant de choisir l'interface
d'affichage avant de lancer le jeu.

## Prérequis

- Python 3 (module standard `curses`, aucune dépendance externe)
- NetHack installé (voir [Chemin de NetHack](#chemin-de-nethack))
- Pour les modes X11 et Qt : une session graphique (`DISPLAY` défini)

## Utilisation

```bash
./nethack_launcher.py
```

Les arguments supplémentaires sont transmis tels quels à NetHack, sauf
`--nethack` (voir [Chemin de NetHack](#chemin-de-nethack)) et `-h`/`--help`,
qui affiche l'aide du lanceur :

```bash
./nethack_launcher.py -u MonPerso
./nethack_launcher.py --help
```

## Raccourci dans le menu des applications

Le script `install.py` ajoute une entrée **NetHack Launcher**, avec son icône,
dans la catégorie **Jeux** du menu :

```bash
./install.py
```

Il installe :

- l'icône `nethack-launcher.svg` dans `~/.local/share/icons/hicolor/scalable/apps/` ;
- le raccourci `nethack-launcher.desktop` dans `~/.local/share/applications/`,
  avec les chemins `Exec` et `Path` adaptés à l'emplacement actuel du projet.

Le raccourci ouvre le lanceur dans l'émulateur de terminal par défaut du bureau
(`Terminal=true`). Si le projet est déplacé, relancez simplement `./install.py`.

Pour désinstaller le raccourci et l'icône :

```bash
./install.py --uninstall
```

Pour l'instant, le script ne fonctionne que sous **Lubuntu** : sur un autre
système, il affiche un avertissement et ne modifie rien.

## Modes disponibles

| N° | Mode     | Option nethack | Affichage graphique requis |
|----|----------|----------------|----------------------------|
| 1  | Terminal | `-wtty`        | Non                        |
| 2  | Curses   | `-wcurses`     | Non                        |
| 3  | X11      | `-wX11`        | Oui (serveur X)            |
| 4  | Qt       | `-wQT`         | Oui (X11 ou Wayland)       |

Le mode X11 nécessite un serveur X (`DISPLAY`) ; le mode Qt fonctionne aussi
sous Wayland (`DISPLAY` ou `WAYLAND_DISPLAY`). Sans affichage adapté (par
exemple en SSH sans redirection X), ces modes apparaissent grisés et ne peuvent
pas être lancés.

Le lanceur détecte aussi les interfaces absentes du binaire NetHack, d'après
les bibliothèques auxquelles il est lié (`libncurses` pour Curses, `libXaw`
pour X11, `libQt` pour Qt). Un mode non compilé apparaît grisé avec la mention
« non compilé dans NetHack ». En cas de doute (binaire statique ou
introuvable), tous les modes restent proposés.

## Touches

| Touche          | Action                          |
|-----------------|---------------------------------|
| `↑` / `↓` ou `k` / `j` | Naviguer dans le menu    |
| `Entrée`        | Lancer le mode sélectionné      |
| `1` à `4`       | Lancer directement un mode      |
| `q` ou `Échap`  | Quitter le lanceur              |

À la fin d'une partie, le menu réapparaît avec un message indiquant si NetHack
s'est terminé normalement ou avec un code d'erreur. En modes X11 et Qt, le
terminal reste occupé tant que la fenêtre du jeu est ouverte.

Le dernier mode lancé est mémorisé dans
`~/.config/nethack-launcher/last_mode` et présélectionné au prochain démarrage.

## Configuration

### Chemin de NetHack

Le lanceur cherche l'exécutable `nethack` dans cet ordre :

1. l'option `--nethack CHEMIN` (ou `--nethack=CHEMIN`) ;
2. la variable d'environnement `NETHACK` ;
3. la commande `nethack` dans le `PATH` ;
4. `~/nh/install/games/nethack` (emplacement par défaut d'une compilation
   depuis les sources) ;
5. `/usr/games/nethack` (paquet de la distribution).

```bash
./nethack_launcher.py --nethack /opt/nethack/nethack
NETHACK=/opt/nethack/nethack ./nethack_launcher.py
```

Si un chemin donné par `--nethack` ou `NETHACK` n'est pas exécutable, le
lanceur s'arrête avec un message d'erreur, sans essayer les emplacements
suivants.

### Modes

La liste des modes se trouve en tête de `nethack_launcher.py`, dans `MODES`.
Chaque mode est un `Mode` avec les champs suivants :

- `label`, `description` : texte affiché dans le menu ;
- `args` : options passées à NetHack (ex. : `["-wX11"]`) ;
- `displays` : variables d'affichage dont l'une doit être définie (vide pour
  un mode texte) ;
- `library` : bibliothèque servant à détecter si l'interface est compilée
  (`None` pour ne pas vérifier).

Pour ajouter un mode, il suffit d'ajouter une entrée à `MODES` ; le menu et
les raccourcis numériques s'adaptent automatiquement.

L'option `-w` passée par le lanceur est prioritaire sur `windowtype` défini
dans `~/.nethackrc`.

## Développement

Les tests utilisent uniquement la bibliothèque standard :

```bash
python3 -m unittest -v
```

Le style est vérifié par [Ruff](https://docs.astral.sh/ruff/) (configuration
dans `ruff.toml`) :

```bash
ruff check .
```

Les deux sont lancés automatiquement par GitHub Actions à chaque push et pull
request (`.github/workflows/ci.yml`), avec Python 3.10, 3.12 et 3.14.

## Licence

Copyright (C) 2026 Le Sanglier des Ardennes

Ce programme est un logiciel libre distribué sous les termes de la
[GNU General Public License v3.0](LICENSE) ou (à votre choix) de toute
version ultérieure. Il est fourni sans aucune garantie.
