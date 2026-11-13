#!/usr/bin/env python3
"""Run the actual PowerShell installer against temporary fake GTA directories."""
from pathlib import Path
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / 'scripts/Install-CinnamonCoffee.ps1'
PWSH = sys.argv[1] if len(sys.argv) > 1 else shutil.which('pwsh')
if not PWSH:
    raise SystemExit('Pass a PowerShell 7 executable path (the installer also supports Windows PowerShell 5.1).')


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}


def run(game, *, installer=INSTALLER, what_if=False, success=True):
    args = [str(PWSH), '-NoLogo', '-NoProfile', '-NonInteractive', '-File', str(installer), '-GameFolder', str(game)]
    if what_if:
        args.append('-WhatIf')
    env = os.environ.copy()
    env.update(XDG_CACHE_HOME=str(TEMP / 'pwsh-cache'), XDG_CONFIG_HOME=str(TEMP / 'pwsh-config'),
               XDG_DATA_HOME=str(TEMP / 'pwsh-data'))
    result = subprocess.run(args, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if success:
        assert result.returncode == 0, result.stdout + result.stderr
    else:
        assert result.returncode != 0, 'Expected installation to reject unsafe input'
    return result


def write(root, relative, content):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


checks = 0


def check(condition, message):
    global checks
    checks += 1
    assert condition, message


with tempfile.TemporaryDirectory(prefix='cinnamon-installer-') as directory:
    TEMP = Path(directory)
    game = TEMP / 'GTA V with spaces'
    game.mkdir()
    write(game, 'GTA5.exe', b'placeholder executable for installer tests')
    old = {
        'scripts/CinnamonCoffee.cs': b'legacy original script',
        'scripts/CinnamonCoffee.3.cs': b'previous edited script',
        'scripts/old copies/CinnamonCoffee - copy.cs': b'nested legacy copy',
        'scripts/old copies/CINNAMONCOFFEE.DLL': b'compiled legacy copy',
        'scripts/other/CinnamonCoffee.vb': b'legacy vb script',
    }
    preserved = {
        'scripts/CinnamonCoffee.cfg': b'partnerVoice=custom-user-setting\ndeviceToken=private-value-must-stay\n',
        'scripts/CinnamonCoffeeALife.ini': b'unique A-Life save',
        'scripts/CinnamonCoffeeSounds/BJSuck_1.wav': b'existing custom sound',
        'scripts/OtherMod.cs': b'another mod must remain',
        'scripts/other/Another.dll': b'another compiled mod must remain',
    }
    for name, data in {**old, **preserved}.items():
        write(game, name, data)
    before = snapshot(game)
    result = run(game, what_if=True)
    check(snapshot(game) == before, '-WhatIf must not alter any file')
    check(not (game / 'CinnamonCoffee-backups').exists(), '-WhatIf must not create backups')

    result = run(game)
    check('Installed exactly one' in result.stdout, 'installer reports successful verification')
    active = [p for p in (game / 'scripts').rglob('*') if p.is_file()
              and p.name.lower().startswith('cinnamoncoffee') and p.suffix.lower() in ('.cs', '.vb', '.dll')]
    check(len(active) == 1 and active[0].name == 'CinnamonCoffee.3.cs', 'exactly one active mod script remains')
    source = (ROOT / 'Mod/scripts/CinnamonCoffee.3.cs').read_bytes()
    check(active[0].read_bytes() == source, 'installed source matches release byte-for-byte')
    backups = list((game / 'CinnamonCoffee-backups').iterdir())
    check(len(backups) == 1, 'one backup directory created outside scripts')
    for name, data in old.items():
        relative = Path(name).relative_to('scripts')
        check((backups[0] / relative).read_bytes() == data, 'backup retains ' + name)
    for name, data in preserved.items():
        check((game / name).read_bytes() == data, 'preserved ' + name)
    for wav in (ROOT / 'Mod/scripts/CinnamonCoffeeSounds').glob('*.wav'):
        destination = game / 'scripts/CinnamonCoffeeSounds' / wav.name
        if wav.name != 'BJSuck_1.wav':
            check(destination.read_bytes() == wav.read_bytes(), 'copies missing sound ' + wav.name)

    run(game)
    check((game / 'scripts/CinnamonCoffee.3.cs').read_bytes() == source, 'repeat installation preserves active version')
    check(len(list((game / 'CinnamonCoffee-backups').iterdir())) == 2, 'repeat installation creates a distinct recoverable backup')
    check((game / 'scripts/CinnamonCoffee.cfg').read_bytes() == preserved['scripts/CinnamonCoffee.cfg'], 'repeat installation preserves cfg')

    wrong = TEMP / 'not a game'
    wrong.mkdir()
    write(wrong, 'scripts/CinnamonCoffee.cs', b'untouched')
    before = snapshot(wrong)
    run(wrong, success=False)
    check(snapshot(wrong) == before, 'invalid game folder is rejected before writes')

    unsafe = TEMP / 'game with linked scripts'
    unsafe.mkdir()
    write(unsafe, 'GTA5.exe', b'placeholder')
    external = TEMP / 'external shared mods'
    external.mkdir()
    write(external, 'CinnamonCoffee.cs', b'outside user files')
    (unsafe / 'scripts').symlink_to(external, target_is_directory=True)
    before = snapshot(external)
    run(unsafe, success=False)
    check(snapshot(external) == before, 'linked scripts root is refused without modifying external files')
    check(not (unsafe / 'CinnamonCoffee-backups').exists(), 'linked scripts root produces no partial backup')

    nested_link = TEMP / 'game with linked subdirectory'
    nested_link.mkdir()
    write(nested_link, 'GTA5.exe', b'placeholder')
    write(nested_link, 'scripts/CinnamonCoffee.cs', b'original must stay active')
    (nested_link / 'scripts/shared').symlink_to(external, target_is_directory=True)
    before = snapshot(nested_link)
    run(nested_link, success=False)
    check(snapshot(nested_link) == before, 'linked nested directory is rejected before any backups or copies')
    check((external / 'CinnamonCoffee.cs').read_bytes() == b'outside user files',
          'linked nested directory preserves external target')

    rollback = TEMP / 'game with conflicting sound folder'
    rollback.mkdir()
    write(rollback, 'GTA5.exe', b'placeholder')
    write(rollback, 'scripts/CinnamonCoffee.cs', b'original to restore')
    write(rollback, 'scripts/CinnamonCoffeeSounds', b'blocking file with user contents')
    run(rollback, success=False)
    check((rollback / 'scripts/CinnamonCoffee.cs').read_bytes() == b'original to restore', 'failure restores original active script')
    check(not (rollback / 'scripts/CinnamonCoffee.3.cs').exists(), 'failure removes newly installed script')
    check(not (rollback / 'scripts/CinnamonCoffee.cfg').exists(), 'failure removes newly created cfg')
    check((rollback / 'scripts/CinnamonCoffeeSounds').read_bytes() == b'blocking file with user contents', 'failure retains conflicting user file')

    # Exercise the layout used in the ZIP, including source/destination coincidence.
    packaged = TEMP / 'package layout'
    packaged.mkdir()
    shutil.copyfile(INSTALLER, packaged / 'Install-CinnamonCoffee.ps1')
    shutil.copytree(ROOT / 'Mod/scripts', packaged / 'scripts')
    write(packaged, 'GTA5_Enhanced.exe', b'placeholder')
    cfg_before = (packaged / 'scripts/CinnamonCoffee.cfg').read_bytes()
    run(packaged, installer=packaged / 'Install-CinnamonCoffee.ps1')
    check((packaged / 'scripts/CinnamonCoffee.3.cs').read_bytes() == source, 'package extracted directly into game folder installs successfully')
    check((packaged / 'scripts/CinnamonCoffee.cfg').read_bytes() == cfg_before, 'in-place source cfg preserved')

print(f'PASS: {checks} actual PowerShell installer assertions (temporary fake game folders, no GTA V runtime).')
