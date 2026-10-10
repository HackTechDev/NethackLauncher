# NetHack Launcher

Lanceur en mode terminal (TUI) pour NetHack, permettant de choisir l'interface
d'affichage avant de lancer le jeu.

## Prérequis

- Python 3 (module standard `curses`, aucune dépendance externe)
- NetHack installé dans `/home/util01/nh/install/games/nethack`
- Pour les modes X11 et Qt : une session graphique (`DISPLAY` défini)

## Utilisation

```bash
./nethack_launcher.py
```

Les arguments supplémentaires sont transmis tels quels à NetHack :

```bash
./nethack_launcher.py -u MonPerso
```

## Raccourci dans le menu des applications

Le fichier `nethack-launcher.desktop` ajoute une entrée **NetHack Launcher**
dans la catégorie **Jeux** du menu. Pour l'installer :

```bash
install -m 644 nethack-launcher.desktop ~/.local/share/applications/
```

Le raccourci ouvre le lanceur dans l'émulateur de terminal par défaut du bureau
(`Terminal=true`). Les chemins `Exec`, `Path` et `Icon` sont absolus : adaptez-les
si le projet ou NetHack est déplacé. Pour le désinstaller :

```bash
rm ~/.local/share/applications/nethack-launcher.desktop
```

## Modes disponibles

| N° | Mode     | Option nethack | Affichage graphique requis |
|----|----------|----------------|----------------------------|
| 1  | Terminal | `-wtty`        | Non                        |
| 2  | Curses   | `-wcurses`     | Non                        |
| 3  | X11      | `-wX11`        | Oui                        |
| 4  | Qt       | `-wQT`         | Oui                        |

Sans affichage graphique (par exemple en SSH sans redirection X), les modes
X11 et Qt apparaissent grisés et ne peuvent pas être lancés.

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

## Configuration

Le chemin de l'exécutable et la liste des modes se trouvent en tête de
`nethack_launcher.py` :

- `NETHACK` : chemin du script de lancement de NetHack
- `MODES` : liste de tuples `(libellé, description, options, nécessite X)`

Pour ajouter un mode, il suffit d'ajouter une entrée à `MODES` ; le menu et
les raccourcis numériques s'adaptent automatiquement.

L'option `-w` passée par le lanceur est prioritaire sur `windowtype` défini
dans `~/.nethackrc`.
