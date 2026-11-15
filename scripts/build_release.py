#!/usr/bin/env python3
"""Build and verify the downloadable package without running GTA V."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'releases/CinnamonCoffee-club-dance-1.3.zip'
LATEST = ROOT / 'releases/CinnamonCoffee-live-voices.zip'


def main():
    # Publish program/assets, never a local A-Life save or the new club tip ledger.
    sources = [ROOT / 'Mod/scripts/CinnamonCoffee.3.cs', ROOT / 'Mod/scripts/CinnamonCoffee.cfg']
    sources += sorted((ROOT / 'Mod/scripts/CinnamonCoffeeSounds').glob('*.wav'))
    assert len(list((ROOT / 'Mod/scripts/CinnamonCoffeeSounds').glob('*.wav'))) == 31
    assert (ROOT / 'Mod/scripts/CinnamonCoffee.3.cs') in sources
    assert not (ROOT / 'Mod/scripts/CinnamonCoffee.cs').exists(), 'Do not package duplicate scripts'
    files = {str(p.relative_to(ROOT / 'Mod')).replace('\\', '/'): p.read_bytes() for p in sources}
    files['README_PL.md'] = (ROOT / 'README.md').read_bytes()
    files['Install-CinnamonCoffee.ps1'] = (ROOT / 'scripts/Install-CinnamonCoffee.ps1').read_bytes()
    PACKAGE.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(PACKAGE, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(PACKAGE) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(files)
        for name, data in files.items():
            assert archive.read(name) == data, name
    LATEST.write_bytes(PACKAGE.read_bytes())
    print(f'Verified package: {PACKAGE} ({PACKAGE.stat().st_size} bytes, {len(files)} files)')


if __name__ == '__main__':
    main()
