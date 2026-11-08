# Audit des divergences Geeetech Mizar S par rapport à Marlin

## Périmètre et méthode

Cet audit compare le sous-dépôt firmware `Marlin2.0.7/` du dépôt Geeetech Mizar S à l'arbre officiel Marlin du tag **2.0.7.2** (commit `88a2ac92d5792de3de005b3b97d7bb561946c148`). Le dépôt Geeetech est référencé à `d3656d6db4bb89f552f9afd3aec013db02a1cff9`. Les comparaisons portent sur les chemins et les identifiants SHA Git des fichiers, puis sur une lecture ciblée des configurations et des zones sensibles. Les ressources binaires et les fichiers d'interface sont comptés dans la comparaison de contenu mais ne sont pas tous interprétables comme du code.

**Résultat structurel (fichiers, sans répertoires)** : 2 026 fichiers côté Geeetech et 2 033 côté Marlin de référence; 1 871 fichiers identiques, **139 fichiers modifiés**, **16 ajoutés** et **23 supprimés**. Les suppressions comprennent des éléments de documentation/workflow amont et des renommages de fichiers MKS; elles ne signifient pas automatiquement une fonctionnalité firmware retirée. Les nombres comparent les contenus de dépôt; ils ne prétendent pas mesurer l'ampleur fonctionnelle ligne par ligne.

La version embarquée visée est celle annoncée par Geeetech, **MizarS_FM_V201A_230512**. Le dépôt source est une branche Marlin 2.0.7 fortement personnalisée et n'est pas une copie binaire reconstruite bit à bit de cette release.

## Résumé des adaptations identifiées

### 1. Carte et chaîne de compilation

- Carte principale sélectionnée : `BOARD_GTM32_LCD35_A10`, avec définitions de broches propres à la carte GTM32 et au TFT35.
- Ajout de cartes et fichiers de configuration de broches Geeetech, d'un linker script STM32 dédié et d'un script PlatformIO dédié.
- Environnement recommandé par le dépôt : `geeetech_lcd35`, basé sur STM32F103VE; le `default_envs` du dépôt pointe sur cet environnement. PlatformIO génère `firmware.bin`, puis le workflow de cette branche le copie sous le nom requis par le bootloader GTM32 : `GTM32Source.bin`.
- Le script de build injecte les paramètres spécifiques au bootloader/à la mémoire et au modèle d'écran. Ce script est donc une dépendance réelle de la production du binaire, pas un simple raccourci.
- Paramètres machine configurés pour l'imprimante : un extrudeur, thermistances de buse et plateau, géométrie/course, fins de course, pas moteurs, limites de température et réglages PID, ainsi que capteur de nivellement propre à la machine.

### 2. Interface graphique MKS LVGL

La personnalisation la plus étendue touche `Marlin/src/lcd/extui/lib/mks_ui/`: écran tactile couleur, menus Geeetech, navigation, dialogues, écran d'impression, réglages, traductions et chargement des ressources graphiques (`assets`). Cette interface a ses propres chemins d'exécution en plus de l'interface LCD standard de Marlin.

Conséquence opérationnelle : le binaire seul ne suffit pas toujours à restaurer l'interface. La procédure Geeetech demande le répertoire `assets` sur la carte TF avec le firmware. Le workflow de cette branche extrait maintenant les assets officiels de `Resource/MizarS_FM_V201A_230512.rar` et contrôle les 107 noms listés ainsi que la police originale `FontUNIGBK.bin`. Il n'utilise plus les substitutions MKS. L'artefact ajoute séparément des aperçus PNG décodés; ceux-ci ne remplacent pas les fichiers `.bin` officiels à placer sur la carte.

Les fichiers d'écran modifiés sont listés ci-dessous; les changements MKS sont distribués dans de nombreux fichiers, pas encapsulés dans un unique module.

### 3. Détection de filament et pause/reprise

- La configuration Marlin active les entrées de détection de filament et associe leur logique à l'écran MKS et au mécanisme de pause/changement de filament.
- Les personnalisations concernent l'observation des capteurs, la génération de la pause, les dialogues tactiles, les déplacements/positions de pause et la reprise du travail.
- Dans le code d'origine Geeetech, la détection et la pause sont présentes, mais le dialogue de l'écran est couplé à son propre état d'interface. Le chemin « filament réinséré → acquittement écran → reprise » doit être vérifié indépendamment du simple déclenchement du capteur.
- Sur la branche d'audit, les correctifs Codex font partie du delta par rapport à Geeetech : le dialogue d'acquittement vérifie les capteurs configurés avant la reprise et attend l'état de pause; le polling évite le double comptage et préserve le feedrate pour la reprise. Ils ne sont donc pas attribués au firmware original.
- Tests imprimante rapportés comme réussis par l'utilisateur : détection de fin de filament, insertion et purge manuelle, acquittement et reprise sans redémarrage. Les scénarios supplémentaires restent à couvrir : plusieurs capteurs s'il y en a, reprise après annulation, et comportement si le filament est retiré à nouveau pendant la reprise.

### 4. Reprise après coupure (PLR)

La configuration d'origine active `POWER_LOSS_RECOVERY` avec stockage EEPROM et sauvegarde de position Z. Le code Geeetech modifie `powerloss.cpp/.h`, `M24_M25.cpp`, `M1001.cpp` et les paramètres EEPROM.

Dans le code observé, le mécanisme :
- conserve position, position Z nivelée, fichier/offset SD, temps, températures cibles, ventilateurs, état de nivellement, modes relatifs et paramètres utiles à la reprise;
- vérifie au démarrage s'il existe un état valide et injecte `M1000 S` pour déclencher l'écran/commande de récupération;
- restaure la position, réchauffe les éléments, puis rouvre le fichier et relance depuis l'offset mémorisé.

Points de vigilance pour la validation :
- la validité et la fraîcheur des données EEPROM après coupure réelle, arrêt normal, nouvelle impression et absence de données doivent toutes être exercées;
- le chemin de reprise contient des séquences G-code spécifiques (homing, chauffe, restauration de Z/XY/E et `M24`); la bonne position dépend de la géométrie, du capteur et du type de coupure;
- la récupération est liée à une impression depuis SD et ne prouve pas une reprise d'un travail envoyé en série;
- le code appelle le chauffage avant la reprise avec une condition fondée sur la température de la buse 0; confirmer le comportement lorsque la cible enregistrée est nulle ou que l'état sauvegardé est incomplet.
  
Ces points sont des risques de test dérivés du chemin de code, pas l'affirmation qu'une panne a été reproduite. La validation logicielle par compilation ne peut pas démontrer une coupure d'alimentation physique.

### 5. Nivellement, homing et mouvement

Des écarts sont répartis dans le palpage et le nivellement ABL/mesh, G28, G29, G42, M420/M421, BLTouch générique, positionnement, planificateur, moteur pas-à-pas et fins de course. Ils adaptent Marlin au capteur et aux coordonnées de la Mizar S. Toute modification de cette zone peut affecter l'homing, les limites de course, la reprise PLR et la collision tête/plateau; elle doit être validée avec les positions réelles.

### 6. Autres adaptations transversales

Les autres changements touchent la gestion des commandes G-code, pause M0/M1/M600, SD M24/M25, température et protections, EEPROM, buzzer, chronomètre et traitement des macros/conditions. Certains fichiers amont supprimés sont de la documentation ou des workflows du dépôt et non du firmware embarqué.

### 7. Mémorisation du mode LED

Le changelog V1.9.3 mentionne la mémorisation de l'état de la LED. Dans le code public Geeetech, le réglage est bien écrit en EEPROM après l'action de l'écran et relu au démarrage, mais il est stocké dans un booléen : éteint ou allumé. Si allumé, `MarlinCore.cpp` force le mode couleur; le choix blanc/couleur n'est pas mémorisé. Cela explique que la LED revienne en couleurs même si le mode blanc avait été choisi. La formulation du changelog peut désigner le seul état marche/arrêt; le code ne préserve toutefois pas le mode d'éclairage sélectionné.

La branche étend ce champ à trois états : `0=éteint`, `1=couleur`, `2=blanc`. Le mode couleur garde la valeur EEPROM `1`, ce qui préserve le comportement des anciennes sauvegardes; le champ reste sur un octet et son emplacement dans les données EEPROM n'est pas déplacé. Au démarrage, le firmware restaure maintenant la valeur correspondante et l'état de l'interface. Cette correction doit encore être validée sur l'imprimante en testant les trois modes après redémarrage et l'enregistrement par `M500`.

## Delta ajouté sur la branche d'audit

À distinguer des personnalisations du fournisseur :
- `printer_operation.cpp` : correction de l'échantillonnage/anti-rebond du capteur et sauvegarde de la vitesse avant pause;
- `draw_dialog.cpp` : validation du retour capteur et transition explicite vers la reprise depuis le dialogue;
- `MarlinCore.cpp`, `MarlinCore.h`, `settings.cpp` et `draw_set.cpp` : mémorisation des trois états LED et restauration du mode choisi au démarrage, avec compatibilité pour les anciennes sauvegardes EEPROM;
- `geeetech_lcd35.py` : itération sur une copie de `CPPDEFINES` pour éviter la mutation de la collection pendant son parcours dans l'environnement GitHub Actions;
- workflow GitHub Actions et documentation de compilation/récupération.

La compilation GitHub du profil Geeetech `geeetech_lcd35` a réussi sur le commit final de code `5e3f1c65a18958ddf1b726779220e84620483e44`; [workflow firmware-build #29](https://github.com/SounMayon/Mizar-S/actions/runs/42535845365). La chaîne a été exécutée dans GitHub Actions avec restauration des assets officiels. Depuis, l'utilisateur a confirmé les tests sur l'imprimante de la détection de fin de filament suivie de la reprise après insertion/purge manuelle, ainsi que la reprise après coupure de courant. Ces résultats matériels rapportés par l'utilisateur ne valident ni la nouvelle mémorisation du mode LED ni M600, qui reste désactivé.

## Inventaire exhaustif des chemins divergents

Les chemins ci-dessous désignent le sous-répertoire `Marlin2.0.7/` du dépôt Geeetech. « Modifié » signifie que le blob diffère du blob au même chemin dans Marlin 2.0.7.2.

### Modifiés — configuration
`Marlin/Configuration.h`, `Marlin/Configuration_adv.h`

### Modifiés — interface MKS/LVGL
`Marlin/src/lcd/extui/lib/mks_ui/SPI_TFT.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_about.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_about.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_acceleration_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_advance_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_baby_stepping.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_baby_stepping.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_change_speed.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_change_speed.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_dialog.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_dialog.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_eeprom_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_encoder_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_error_message.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_extrusion.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_extrusion.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_fan.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_filament_change.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_filament_change.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_filament_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_home.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_homing_sensitivity_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_jerk_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_keyboard.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_language.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_level_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_machine_para.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_machine_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_manuaLevel.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_manuaLevel.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_manual_level_pos_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_max_feedrate_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_motor_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_move_motor.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_number_key.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_operation.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_operation.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_pause_position.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_preHeat.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_preHeat.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_print_file.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_printing.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_printing.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_ready_print.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_set.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_set.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_step_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_tmc_current_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_tmc_step_mode_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_tool.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_tool.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_ui.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_ui.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_wifi.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_wifi_list.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_wifi_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_wifi_tips.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/gb2312_puhui16.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/mks_hardware_test.h`, `Marlin/src/lcd/extui/lib/mks_ui/pic_manager.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/pic_manager.h`, `Marlin/src/lcd/extui/lib/mks_ui/printer_operation.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_en.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_fr.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_it.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_ru.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_s_cn.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_sp.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_Language_t_cn.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_lvgl_configuration.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/tft_lvgl_configuration.h`, `Marlin/src/lcd/extui/lib/mks_ui/tft_multi_language.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/tft_multi_language.h`, `Marlin/src/lcd/extui/lib/mks_ui/wifi_module.cpp`

### Modifiés — noyau Marlin, G-code, mouvement, capteurs et build
`Marlin/src/HAL/STM32F1/watchdog.h`, `Marlin/src/MarlinCore.cpp`, `Marlin/src/MarlinCore.h`, `Marlin/src/core/boards.h`, `Marlin/src/feature/bedlevel/abl/abl.cpp`, `Marlin/src/feature/bedlevel/abl/abl.h`, `Marlin/src/feature/bedlevel/bedlevel.cpp`, `Marlin/src/feature/bedlevel/bedlevel.h`, `Marlin/src/feature/bedlevel/mbl/mesh_bed_leveling.cpp`, `Marlin/src/feature/bedlevel/mbl/mesh_bed_leveling.h`, `Marlin/src/feature/bltouch.cpp`, `Marlin/src/feature/bltouch.h`, `Marlin/src/feature/direct_stepping.cpp`, `Marlin/src/feature/powerloss.cpp`, `Marlin/src/feature/powerloss.h`, `Marlin/src/gcode/bedlevel/G26.cpp`, `Marlin/src/gcode/bedlevel/G42.cpp`, `Marlin/src/gcode/bedlevel/M420.cpp`, `Marlin/src/gcode/bedlevel/abl/G29.cpp`, `Marlin/src/gcode/bedlevel/abl/M421.cpp`, `Marlin/src/gcode/bedlevel/mbl/G29.cpp`, `Marlin/src/gcode/bedlevel/mbl/M421.cpp`, `Marlin/src/gcode/calibrate/G28.cpp`, `Marlin/src/gcode/calibrate/G76_M192_M871.cpp`, `Marlin/src/gcode/calibrate/M48.cpp`, `Marlin/src/gcode/control/T.cpp`, `Marlin/src/gcode/feature/pause/M600.cpp`, `Marlin/src/gcode/gcode.cpp`, `Marlin/src/gcode/lcd/M0_M1.cpp`, `Marlin/src/gcode/queue.cpp`, `Marlin/src/gcode/sd/M1001.cpp`, `Marlin/src/gcode/sd/M24_M25.cpp`, `Marlin/src/gcode/temp/M104_M109.cpp`, `Marlin/src/gcode/temp/M140_M190.cpp`, `Marlin/src/gcode/units/M82_M83.cpp`, `Marlin/src/inc/Conditionals_LCD.h`, `Marlin/src/inc/Conditionals_adv.h`, `Marlin/src/inc/Conditionals_post.h`, `Marlin/src/inc/SanityCheck.h`, `Marlin/src/inc/Version.h`, `Marlin/src/lcd/extui/ui_api.cpp`, `Marlin/src/lcd/ultralcd.cpp`, `Marlin/src/lcd/ultralcd.h`, `Marlin/src/libs/buzzer.cpp`, `Marlin/src/libs/buzzer.h`, `Marlin/src/libs/numtostr.cpp`, `Marlin/src/libs/stopwatch.cpp`, `Marlin/src/libs/stopwatch.h`, `Marlin/src/module/endstops.cpp`, `Marlin/src/module/endstops.h`, `Marlin/src/module/motion.cpp`, `Marlin/src/module/motion.h`, `Marlin/src/module/planner.cpp`, `Marlin/src/module/probe.cpp`, `Marlin/src/module/probe.h`, `Marlin/src/module/settings.cpp`, `Marlin/src/module/settings.h`, `Marlin/src/module/stepper.cpp`, `Marlin/src/module/temperature.cpp`, `Marlin/src/module/temperature.h`, `Marlin/src/pins/pins.h`, `Marlin/src/sd/cardreader.cpp`
`platformio.ini`

### Ajoutés par Geeetech
`Marlin/src/lcd/extui/lib/mks_ui/draw_autoLevel.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_autoLevel.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_autolevel_menu.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_autolevel_menu.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_autolevel_offset_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_autolevel_offset_settings.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_handHeat.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_handHeat.h`, `Marlin/src/lcd/extui/lib/mks_ui/draw_more.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_more.h`, `Marlin/src/pins/mega/pins_GT2560_V3.0.h`, `Marlin/src/pins/stm32f1/pins_GTM32_LCD35_A10.h`, `Marlin/src/pins/stm32f1/pins_GTM32_LCD35_A30.h`, `Marlin/src/pins/stm32f1/pins_GTM32_LCD35_E180.h`, `buildroot/share/PlatformIO/ldscripts/geeetech_lcd35.ld`, `buildroot/share/PlatformIO/scripts/geeetech_lcd35.py`

### Supprimés par Geeetech
`.github/FUNDING.yml`, `.github/ISSUE_TEMPLATE/bug_report.md`, `.github/ISSUE_TEMPLATE/config.yml`, `.github/ISSUE_TEMPLATE/feature_request.md`, `.github/code_of_conduct.md`, `.github/contributing.md`, `.github/issue_template.md`, `.github/lock.yml`, `.github/pull_request_template.md`, `.github/workflows/bump-date.yml`, `.github/workflows/check-pr.yml`, `.github/workflows/close-stale.yml`, `.github/workflows/lock-closed.yml`, `.github/workflows/test-builds.yml`, `.github/workflows/unlock-reopened.yml`, `Marlin/lib/readme.txt`, `Marlin/src/lcd/extui/lib/mks_ui/draw_auto_level_offset_settings.cpp`, `Marlin/src/lcd/extui/lib/mks_ui/draw_auto_level_offset_settings.h`, `Marlin/src/sd/usb_flashdrive/lib-uhs2/README.txt`, `Marlin/src/sd/usb_flashdrive/lib-uhs3/README.txt`, `buildroot/share/PlatformIO/variants/CHITU_F103/wirish/start.S`, `buildroot/share/PlatformIO/variants/MEEB_3DP/wirish/start.S`, `buildroot/share/cmake/CMakeLists.txt`

## Références

- [Dépôt source officiel Geeetech Mizar S](https://github.com/Geeetech3D/Mizar-S)
- [Configuration PlatformIO Geeetech](https://github.com/Geeetech3D/Mizar-S/blob/main/Marlin2.0.7/platformio.ini)
- [Marlin officiel 2.0.7.2](https://github.com/MarlinFirmware/Marlin/tree/2.0.7.2)
- [Procédure Geeetech de mise à jour](https://wiki.geeetech.com/index.php/Geeetech_Mizar_S_3D_Printer#Update_Firmware)

## Vérification complémentaire des assets

Le dépôt officiel Geeetech Mizar S expose 107 fichiers JPG dans `Resource/icon/`, dont les noms correspondent aux 107 entrées `.bin` de `Resource/list.txt` après remplacement de l'extension. Il fournit également `Resource/font/FontUNIGBK.bin`, une liste de caractères `tft_font_total.txt`, le code d'accès à la police et des outils LVGL. Les JPG et les outils sont utiles pour examiner ou modifier les sources graphiques, mais les binaires de l'archive officielle restent les ressources validées pour le flashage.

La documentation Geeetech du convertisseur d'images précise que la génération C a été testée et que le format `.bin` n'avait pas été utilisé/validé dans cet outil. Il ne faut donc pas remplacer les `.bin` de l'archive officielle par une conversion issue de cet outil sans validation du format et de l'affichage. Les substitutions d'icônes MKS testées précédemment ont provoqué des icônes coupées ou absentes et du texte manquant; elles sont abandonnées.

## Audit des autres dépôts publics Geeetech3D

L'inventaire public de l'organisation comprend les projets d'imprimantes Prusa i3, Mizar, Mizar S, Mizar Pro, Spark E3 et Kirin, les outils Smartto, Cura, Diagram, Knowledge, ainsi que les dépôts `Marlin-Beta-Releases` et `Custom-firmwares`. Les liens et les conclusions ci-dessous sont un audit de pertinence pour cette branche Mizar S, pas une validation ligne par ligne de chaque produit de l'organisation.

- **Mizar S :** [dépôt source officiel](https://github.com/Geeetech3D/Mizar-S) confirmé comme référence principale. Son README indique Marlin 2.0.7 et précise que le code est destiné à la Mizar S et à son écran d'origine. La source principale est équivalente à la base utilisée ici pour les points examinés; aucun correctif M600 activé ou portage MKS plus complet n'y a été trouvé.
- **Assets Mizar S :** [sources des icônes et outils LVGL](https://github.com/Geeetech3D/Mizar-S/tree/main/Resource) constituent une référence utile pour inspecter les fichiers, les caractères et les images originales. La [note du convertisseur](https://github.com/Geeetech3D/Mizar-S/blob/main/Resource/Lvgl_image_convert_tool/Readme.md) indique que la sortie binaire n'était pas encore éprouvée, d'où la conservation des assets `.bin` de l'archive officielle dans le workflow.
- **M600 :** dans le dépôt officiel, `M600.cpp` existe car Marlin 2.0.7 contient l'implémentation générique, mais `ADVANCED_PAUSE_FEATURE` est commenté dans `Configuration_adv.h`; cette option requiert aussi `NOZZLE_PARK_FEATURE`. Les callbacks de dialogues de pause sont conditionnels, et la recherche du callback ExtUI `onUserConfirmRequired` ne trouve pas d'implémentation MKS. La branche laisse donc M600 désactivé tant que l'interface tactile et le build ne sont pas portés ensemble.
- **Autres modèles Mizar/Mizar Pro :** [Mizar](https://github.com/Geeetech3D/Mizar) et [Mizar Pro](https://github.com/Geeetech3D/Mizar-Pro) partagent un socle Marlin 2.0.7, mais leurs configurations et variantes matérielles sont propres à ces machines. Les réglages, broches et ressources ne sont pas transposés à la Mizar S sans preuve d'identité matérielle.
- **Dépôts A10/A20 historiques :** [Marlin-Beta-Releases](https://github.com/Geeetech3D/Marlin-Beta-Releases) et [Custom-firmwares](https://github.com/Geeetech3D/Custom-firmwares) ciblent des cartes GT2560 A10/A20 et des firmwares AVR `.hex`; ils ne fournissent pas de source ou de binaire GTM32 LCD35 Mizar S à réutiliser.
- **Autres dépôts de l'organisation :** Prusa_I3_3Dprinter, Smartto-Eclipse, Smartto-Tool, Smartto-IAR, Cura, Diagram, Knowledge, Geeetech-Spark-E3 et Geeetech-Kirin concernent d'autres produits, logiciels ou cartes. Aucun correctif Mizar S directement réutilisable n'a été identifié; ne pas reprendre leur firmware sans confirmer la carte, l'écran et le brochage.
- **Leçon de compilation :** l'[issue #1 du dépôt officiel Mizar S](https://github.com/Geeetech3D/Mizar-S/issues/1) rapporte un échec avec l'environnement générique `STM32F103RE`, notamment parce que le MCU ciblé ne fournit pas le contrôleur FSMC attendu. La branche compile avec l'environnement recommandé Geeetech `geeetech_lcd35` et le script/linker spécifiques GTM32; cet ancien rapport renforce qu'il ne faut pas substituer un environnement générique au profil fournisseur.

Cette recherche n'a trouvé aucune archive publique Geeetech contenant le code source exact correspondant à `MizarS_FM_V201A_230512`. Le dépôt officiel fournit le code Marlin personnalisé et les assets, tandis que le paquet V2.0.1 fourni par l'utilisateur apporte le binaire compilé et les ressources associées. Le changelog peut donc mentionner des changements absents du code source public actuellement examiné.

## Limites

Cet audit est une comparaison complète de l'inventaire des fichiers du sous-dépôt firmware, complétée par l'analyse ciblée des flux de configuration, d'interface, de pause et de récupération. Il ne certifie pas chaque ligne modifiée comme sûre, ni la correspondance exacte entre chaque ligne source et le binaire officiel distribué. Les vérifications électromécaniques, thermiques et de reprise nécessitent la Mizar S et ne peuvent être conclues depuis GitHub Actions.
