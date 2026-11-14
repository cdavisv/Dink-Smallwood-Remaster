"""Tests for Scripts/check_package_content.py (string-path assets must be in the package)."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import check_package_content as cpc  # noqa: E402


def _touch(path: Path, text: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _listing(*packages: str) -> str:
    return "\n".join(
        f'[0]LogIoStore: Display: "../../../DinkRemaster/Content/{p}.uasset" offset: 0, size: 1 bytes'
        for p in packages)


class CheckPackageContentTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.project = Path(self.tmp.name)
        _touch(self.project / "Content/Dink/Photoreal/Props/SM_Bed_PR.uasset")
        _touch(self.project / "Content/Dink/Kits/SM_Wall.uasset")
        _touch(self.project / "Content/Dink/Data/Art/families.json",
               '{"a": "/Game/Dink/Photoreal/Props/SM_Bed_PR.SM_Bed_PR", "b": "/Game/Dink/Kits/SM_Wall",'
               ' "never_imported": "/Game/Dink/Photoreal/Props/SM_Absent_PR"}')
        _touch(self.project / "Plugins/DinkCore/Source/DinkCore/Private/Art.cpp",
               'LoadObject(TEXT("/Game/Dink/Kits/SM_Wall.SM_Wall")); Printf(TEXT("/Game/Dink/Photoreal/%s"));')
        # Test sources are not runtime references.
        _touch(self.project / "Plugins/DinkCore/Source/DinkCore/Private/Tests/ArtTests.cpp",
               'TEXT("/Game/Dink/Kits/SM_TestOnly")')
        _touch(self.project / "Content/Dink/Kits/SM_TestOnly.uasset")

    def tearDown(self):
        self.tmp.cleanup()

    def test_package_paths_strip_object_names(self):
        self.assertEqual(cpc.packages_in_text('"/Game/A/B/C.C" and /Game/A/D:Sub'), {"/Game/A/B/C", "/Game/A/D"})

    def test_listing_parser_reads_iostore_lines(self):
        self.assertEqual(cpc.packaged_set(_listing("Dink/Kits/SM_Wall")), {"/Game/Dink/Kits/SM_Wall"})

    def test_missing_photoreal_package_fails(self):
        missing, required, _ = cpc.check(self.project, _listing("Dink/Kits/SM_Wall"))
        self.assertEqual(required, 2)  # never-imported and test-only paths do not count
        self.assertEqual([m[0] for m in missing], ["/Game/Dink/Photoreal/Props/SM_Bed_PR"])

    def test_complete_package_passes(self):
        missing, _, _ = cpc.check(self.project, _listing("Dink/Kits/SM_Wall", "Dink/Photoreal/Props/SM_Bed_PR"))
        self.assertEqual(missing, [])

    def test_main_exit_codes(self):
        listing = self.project / "listing.txt"
        listing.write_text(_listing("Dink/Kits/SM_Wall"), encoding="utf-8")
        self.assertEqual(cpc.main(["--project", str(self.project), "--listing", str(listing)]), 1)
        listing.write_text(_listing("Dink/Kits/SM_Wall", "Dink/Photoreal/Props/SM_Bed_PR"), encoding="utf-8")
        self.assertEqual(cpc.main(["--project", str(self.project), "--listing", str(listing)]), 0)

    def test_package_script_cooks_photoreal(self):
        script = (Path(__file__).resolve().parent.parent / "package.sh").read_text(encoding="utf-8")
        self.assertIn("Dink/Photoreal ", script)
        self.assertIn("check_package_content.py", script)


if __name__ == "__main__":
    unittest.main()
