"""saved_picture_keys: the pictures story scripts save for a placement (editor_seq / editor_frame) reach the import bundle."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sync_gameplay_data import saved_picture_keys

SEQUENCES = [
    {"seq": 173, "frames": [{"frame": f, "width": 56, "height": 55, "image": f"sprites/173/{f:02d}.png"} for f in range(1, 7)]},
    {"seq": 175, "frames": [{"frame": f, "width": 44, "height": 60, "image": f"sprites/175/{f:02d}.png"} for f in range(1, 7)]},
]

BARREL = """void hit( void )
{
  int &hold = sp_editor_num(&current_sprite);
  if (&hold != 0)
  {
     editor_type(&hold, 3);
     editor_seq(&hold, 173);
     editor_frame(&hold, 6);
  }
}"""
CHEST = BARREL.replace("173", "175").replace("editor_frame(&hold, 6)", "editor_frame(&hold, 4)").replace("editor_type(&hold, 3)", "editor_type(&hold, 4)")


class SavedPictureKeys(unittest.TestCase):
    def test_pairs_seq_and_frame_of_each_script(self):
        keys = saved_picture_keys({"bar-sh": BARREL, "ch1-ap": CHEST, "plain": "void main( void ) { }"}, SEQUENCES)
        self.assertEqual(keys, {"173_06": "sprites/173/06.png", "175_04": "sprites/175/04.png"})

    def test_missing_frame_refuses(self):
        with self.assertRaises(ValueError):
            saved_picture_keys({"odd": BARREL.replace("editor_frame(&hold, 6)", "editor_frame(&hold, 9)")}, SEQUENCES)


if __name__ == "__main__":
    unittest.main()
