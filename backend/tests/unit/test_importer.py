import io
import zipfile

import pytest

from backend.projects.importer import (
    ImportError_,
    files_from_directory,
    files_from_zip,
    find_project_dirs,
)

INVENTORY = "﻿id_evidencia;projeto_id;tipo;arquivo;conteudo_esperado;status;observacao\nPRJ90-EV01;PRJ90;Dossiê;dossie_projeto.pdf;x;Localizada;síntese\n"


def make_zip(entries: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def test_zip_strips_single_top_folder():
    files = files_from_zip(make_zip({"PRJ90/metodo.md": b"# m", "PRJ90/evidencias/medicoes.csv": b"a;b"}))
    assert sorted(f.path for f in files) == ["evidencias/medicoes.csv", "metodo.md"]
    assert files_from_zip(make_zip({"PRJ90/metodo.md": b"x"}))[0].top_folder == "PRJ90"


def test_zip_keeps_paths_without_common_folder():
    files = files_from_zip(make_zip({"a.md": b"1", "evidencias/b.csv": b"2"}))
    assert sorted(f.path for f in files) == ["a.md", "evidencias/b.csv"]


def test_zip_rejects_path_traversal():
    with pytest.raises(ImportError_, match="unsafe"):
        files_from_zip(make_zip({"../evil.txt": b"x"}))


def test_zip_skips_macos_metadata_and_dirs():
    files = files_from_zip(make_zip({"__MACOSX/._a": b"x", "p/a.md": b"1", "p/.DS_Store": b"x"}))
    assert [f.path for f in files] == ["a.md"]


def test_zip_too_big_is_rejected(monkeypatch):
    monkeypatch.setattr("backend.projects.importer.MAX_TOTAL_BYTES", 10)
    with pytest.raises(ImportError_, match="too large"):
        files_from_zip(make_zip({"a.md": b"x" * 50}))


def test_invalid_zip():
    with pytest.raises(ImportError_):
        files_from_zip(b"not a zip")


def test_directory_walk_returns_relative_posix_paths(tmp_path):
    (tmp_path / "evidencias").mkdir()
    (tmp_path / "evidencias" / "metodo.md").write_text("# m")
    (tmp_path / "dossie.pdf").write_bytes(b"%PDF")
    (tmp_path / ".hidden").write_text("x")
    assert sorted(f.path for f in files_from_directory(tmp_path)) == ["dossie.pdf", "evidencias/metodo.md"]


def test_find_project_dirs_by_inventory_content(tmp_path):
    for name in ("01_historico/PRJ90", "02_casos/caso-x"):
        folder = tmp_path / name
        folder.mkdir(parents=True)
        (folder / "lista.csv").write_text(INVENTORY, encoding="utf-8")
    (tmp_path / "outros").mkdir()
    (tmp_path / "outros" / "notas.csv").write_text("a;b\n1;2\n")
    found = find_project_dirs(tmp_path)
    assert [p.name for p in found] == ["PRJ90", "caso-x"]


def test_find_project_dirs_accepts_project_folder_itself(tmp_path):
    (tmp_path / "inventario.csv").write_text(INVENTORY, encoding="utf-8")
    assert find_project_dirs(tmp_path) == [tmp_path]
