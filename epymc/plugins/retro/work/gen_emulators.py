#!/usr/bin/env python
# This Python file uses the following encoding: utf-8
#
# Copyright (C) 2010-2021 Davide Andreoli <dave@gurumeditation.it>
#
# Generate emulators.ini from a recalbox es_system.cfg
#
# Thanks and credits to the recalbox team !
#

import os
from pathlib import Path
import xml.etree.ElementTree as ElementTree
from operator import itemgetter


script_path = Path(os.path.dirname(__file__))
cfg_path = script_path / 'es_systems.cfg'
ini_path = script_path / 'emulators.ini'
exclude = {
    'favorites',
    'imageviewer',
}

xml_tree = ElementTree.parse(cfg_path)
xml_root = xml_tree.getroot()
outf = open(ini_path, 'w')

for xml_system in xml_root:
    name = xml_system.find('name').text
    fullname = xml_system.find('fullname').text
    if name in exclude:
        print('SKIPPING:', name)
        continue

    # print("\nPARSING:", name, fullname)
    extensions = set(xml_system.find('extension').text.lower().split())
    cores = []
    for xml_emulator in xml_system.findall('emulators/emulator'):
        emulator = xml_emulator.get('name')
        if emulator != 'libretro':
            print('SKIPING NON LIBRETRO EMUALATOR:', name, emulator)
            continue
        for xml_core in xml_emulator.findall('cores/core'):
            core, prio = xml_core.text, xml_core.get('priority')
            cores.append((prio, core))
    if not cores:
        print('SKIPPING NO VALID CORES:', name)
        continue
    cores = [core for pri, core in sorted(cores, key=itemgetter(0))]

    print('GENERATE:', name, extensions, cores)
    outf.write(f'\n[{name}]\n')
    outf.write(f'name={fullname}\n')
    outf.write('emulator=retroarch\n')
    outf.write(f'cores={" ".join(cores)}\n')
    outf.write(f'extensions={" ".join(extensions)}\n')

outf.close()
print("WROTE FILE:", ini_path)
