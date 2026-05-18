"""Tests for path_utils module."""

from pathlib import Path

from path_utils import BASE_DIR, normalize_for_storage, to_absolute, to_relative


class TestToRelative:
    def test_absolute_path_under_base_dir(self):
        abs_path = str(BASE_DIR / "sweet_related_paper" / "papers" / "test.pdf")
        result = to_relative(abs_path)
        assert result == "sweet_related_paper/papers/test.pdf"

    def test_already_relative_path(self):
        result = to_relative("sweet_related_paper/papers/test.pdf")
        assert result == "sweet_related_paper/papers/test.pdf"

    def test_path_from_different_machine(self):
        foreign_path = "/www/wwwroot/FCN_SweetSeek/sweet_related_paper/papers/test.pdf"
        result = to_relative(foreign_path)
        assert result == "sweet_related_paper/papers/test.pdf"

    def test_dual_protein_path_from_different_machine(self):
        foreign_path = "/home/deploy/app/Dual_Protein_related_paper/papers/file.pdf"
        result = to_relative(foreign_path)
        assert result == "Dual_Protein_related_paper/papers/file.pdf"

    def test_unknown_absolute_path_falls_back_to_filename(self):
        result = to_relative("/some/random/path/unknown.pdf")
        assert result == "unknown.pdf"

    def test_empty_string(self):
        assert to_relative("") == ""

    def test_windows_style_path_with_known_anchor(self):
        win_path = "C:\\Users\\user\\project\\sweet_related_paper\\papers\\test.pdf"
        result = to_relative(win_path)
        assert "sweet_related_paper" in result


class TestToAbsolute:
    def test_relative_path(self):
        result = to_absolute("sweet_related_paper/papers/test.pdf")
        expected = str(BASE_DIR / "sweet_related_paper" / "papers" / "test.pdf")
        assert result == expected

    def test_already_absolute_path(self):
        abs_path = "/some/absolute/path.pdf"
        assert to_absolute(abs_path) == abs_path

    def test_empty_string(self):
        assert to_absolute("") == ""


class TestNormalizeForStorage:
    def test_local_absolute_path(self):
        abs_path = str(BASE_DIR / "sweet_related_paper" / "papers" / "file.pdf")
        result = normalize_for_storage(abs_path)
        assert result == "sweet_related_paper/papers/file.pdf"
        assert not Path(result).is_absolute()

    def test_server_absolute_path(self):
        server_path = "/www/wwwroot/FCN_SweetSeek/Dual_Protein_related_paper/papers/protein.pdf"
        result = normalize_for_storage(server_path)
        assert result == "Dual_Protein_related_paper/papers/protein.pdf"

    def test_idempotent(self):
        rel_path = "sweet_related_paper/papers/test.pdf"
        assert normalize_for_storage(rel_path) == rel_path
        assert normalize_for_storage(normalize_for_storage(rel_path)) == rel_path

    def test_roundtrip(self):
        original_rel = "sweet_related_paper/papers/test.pdf"
        abs_path = to_absolute(original_rel)
        back_to_rel = normalize_for_storage(abs_path)
        assert back_to_rel == original_rel
