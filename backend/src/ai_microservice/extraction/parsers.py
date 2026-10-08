"""Parsers determinísticos: csv/xlsx/pdf/md/json → fragmentos com âncora estável.

Contratos (spec 5.1):
- âncora estável: metodo.md#2 (seção), medicoes.csv#PRJ01-S01 (ensaio),
  dossie_projeto.pdf#p3 (página), cronologia.csv#PRJ01-CR01 (id de linha);
- célula vazia → None, nunca 0 (vazio ≠ zero);
- XLSX com cabeçalho na linha 5;
- natureza do fragmento por artefato (depoimento para a transcrição — T9);
- identificação de tipo pelo conteúdo, validada contra inventario_evidencias.csv.
"""
from __future__ import annotations

import csv
import hashlib
import html
import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

# artefato → natureza (schema do pacote uniforme)
NATURE_BY_ARTIFACT = {
    "dossie_projeto.pdf": "sintese",
    "registro_tecnico.pdf": "sintese",
    "transcricao_entrevista_tecnica.pdf": "depoimento",
    "atividades.csv": "registro_primario",
    "atividades.xlsx": "registro_primario",
    "inventario_evidencias.csv": "indice",
    "evidencias/metodo.md": "sintese",
    "evidencias/cronologia.csv": "registro_primario",
    "evidencias/medicoes.csv": "registro_primario",
    "evidencias/resultados.csv": "derivado",
    "evidencias/configuracao.json": "especificacao",
    "evidencias/observacoes.csv": "registro_primario",
    "evidencias/entradas.csv": "registro_primario",
    "evidencias/revisao_tecnica.md": "revisao",
}

# artefato cuja âncora é o valor da coluna id
_ID_COLUMNS = {
    "evidencias/cronologia.csv": "evento_id",
    "evidencias/medicoes.csv": None,  # âncora por ensaio (agrupa registros)
    "evidencias/observacoes.csv": "observacao_id",
    "evidencias/entradas.csv": "entrada_id",
    "evidencias/resultados.csv": "ensaio_id",
    "atividades.csv": "id_atividade",
    "atividades.xlsx": "id_atividade",
    "inventario_evidencias.csv": "id_evidencia",
}

# colunas cuja célula vazia significa null (todas — vazio ≠ zero); valores que
# pareçam numéricos são mantidos como string; a checagem numérica é da CHK.
_GROUP_ANCHOR_COLUMN = {"evidencias/medicoes.csv": "ensaio_id"}


@dataclass
class Fragment:
    anchor: str
    text: str
    nature: str
    data: dict = field(default_factory=dict)
    artifact: str = ""


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]  # strip UTF-8 BOM
    text = raw.decode("utf-8")
    # detecta separador do cabeçalho
    first_line = text.splitlines()[0]
    delim = ";" if first_line.count(";") >= first_line.count(",") else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = list(reader.fieldnames or [])
    rows: list[dict] = []
    for row in reader:
        rows.append({k: (v if v not in (None, "") else None) for k, v in row.items()})
    return headers, rows


def _cell_none_if_empty(v: object) -> object:
    if v is None:
        return None
    s = str(v).strip()
    return s if s else None


def parse_csv(artifact: str, path: Path) -> list[Fragment]:
    headers, rows = _read_csv(path)
    nature = NATURE_BY_ARTIFACT.get(artifact, "registro_primario")
    frags: list[Fragment] = []

    if artifact in _GROUP_ANCHOR_COLUMN:
        # medicoes.csv: âncora por ensaio (grupo de registros do mesmo ensaio)
        group_col = _GROUP_ANCHOR_COLUMN[artifact]
        groups: dict[str, list[dict]] = {}
        for row in rows:
            key = row.get(group_col) or ""
            groups.setdefault(key, []).append(row)
        for key, grows in groups.items():
            lines = [";".join(headers)]
            for r in grows:
                lines.append(";".join("" if r.get(h) is None else str(r.get(h)) for h in headers))
            data: dict = {"registros": grows}
            if len(grows) == 1:
                data.update(grows[0])
            frags.append(
                Fragment(
                    anchor=f"{artifact}#{key}",
                    text="\n".join(lines),
                    nature=nature,
                    data=data,
                    artifact=artifact,
                )
            )
        return frags

    id_col = _ID_COLUMNS.get(artifact)
    for row in rows:
        anchor_key = row.get(id_col) if id_col else None
        if not anchor_key:
            continue
        lines = [";".join(headers)]
        lines.append(";".join("" if row.get(h) is None else str(row.get(h)) for h in headers))
        frags.append(
            Fragment(
                anchor=f"{artifact}#{anchor_key}",
                text="\n".join(lines),
                nature=nature,
                data=row,
                artifact=artifact,
            )
        )
    return frags


def parse_xlsx(artifact: str, path: Path) -> list[Fragment]:
    """XLSX sem openpyxl heavy — lê sheet1.xml; cabeçalho na linha 5."""
    nature = NATURE_BY_ARTIFACT.get(artifact, "registro_primario")
    z = zipfile.ZipFile(path)
    sheet = z.read("xl/worksheets/sheet1.xml").decode("utf-8")
    # shared strings (se houver) e células inline
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        ss = z.read("xl/sharedStrings.xml").decode("utf-8")

        def _clean(s: str) -> str:
            return html.unescape(re.sub(r"<[^>]+>", "", s))

        shared = [_clean(m) for m in re.findall(r"<si>(.*?)</si>", ss, re.S)]
    # células inline (t="str" com <v> inline) e por shared index (t="s")
    rows: dict[int, dict[str, object]] = {}
    for row_xml in re.findall(r"<x:row[^>]*r=\"(\d+)\"[^>]*>(.*?)</x:row>", sheet, re.S):
        rnum = int(row_xml[0])
        cells: dict[str, object] = {}
        for cell_xml in re.findall(r"<x:c\b[^>]*?(?:/>|>.*?</x:c>)", row_xml[1], re.S):
            m_ref = re.search(r'r="([A-Z]+\d+)"', cell_xml)
            m_type = re.search(r't="(\w+)"', cell_xml)
            m_val = re.search(r"<x:v>(.*?)</x:v>", cell_xml, re.S)
            m_inl = re.search(r"<x:is>.*?<x:t[^>]*>(.*?)</x:t>", cell_xml, re.S)
            if not m_ref:
                continue
            ref = m_ref.group(1)
            ctype = m_type.group(1) if m_type else None
            val: object = None
            if ctype == "s" and m_val:
                val = shared[int(m_val.group(1))]
            elif m_inl:
                val = html.unescape(m_inl.group(1))
            elif m_val:
                val = m_val.group(1)
            cells[ref] = val
        rows[rnum] = cells

    if 5 not in rows:
        return []
    header_cells = rows[5]
    headers = [header_cells.get(f"{c}5") for c in "ABCDEFGH"]
    headers = [str(h) for h in headers if h is not None]
    # normaliza cabeçalhos do XLSX para os mesmos nomes do CSV espelho
    _HEADER_ALIASES = {
        "ID da atividade": "id_atividade",
        "Ciclo": "ciclo",
        "Fase": "fase",
        "Natureza informada": "natureza_informada_pela_equipe",
        "Descrição": "descricao",
        "Resultado ou saída": "resultado_ou_saida",
        "Evidências relacionadas": "evidencias_relacionadas",
        "Responsável por função": "responsavel_por_funcao",
    }
    headers = [_HEADER_ALIASES.get(h, h) for h in headers]
    frags: list[Fragment] = []
    for rnum in sorted(r for r in rows if r > 5):
        cells = rows[rnum]
        row: dict = {}
        for i, h in enumerate(headers):
            ref = f"{'ABCDEFGH'[i]}{rnum}"
            row[h] = _cell_none_if_empty(cells.get(ref))
        anchor_key = row.get("ID da atividade") or row.get("id_atividade")
        if not anchor_key:
            continue
        lines = [";".join(headers)]
        lines.append(";".join("" if row.get(h) is None else str(row.get(h)) for h in headers))
        frags.append(
            Fragment(
                anchor=f"{artifact}#{anchor_key}",
                text="\n".join(lines),
                nature=nature,
                data=row,
                artifact=artifact,
            )
        )
    return frags


_MD_SECTION_RE = re.compile(r"^##\s+(\d+)\.\s+(.*)$", re.M)


def parse_md(artifact: str, path: Path) -> list[Fragment]:
    nature = NATURE_BY_ARTIFACT.get(artifact, "sintese")
    text = path.read_text(encoding="utf-8")
    matches = list(_MD_SECTION_RE.finditer(text))
    frags: list[Fragment] = []
    if not matches:
        frags.append(Fragment(anchor=f"{artifact}", text=text, nature=nature, artifact=artifact))
        return frags
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start() : end].strip()
        frags.append(
            Fragment(
                anchor=f"{artifact}#{m.group(1)}",
                text=body,
                nature=nature,
                data={"secao": m.group(1), "titulo": m.group(2)},
                artifact=artifact,
            )
        )
    return frags


def parse_pdf(artifact: str, path: Path) -> list[Fragment]:
    nature = NATURE_BY_ARTIFACT.get(artifact, "sintese")
    reader = PdfReader(str(path))
    frags: list[Fragment] = []
    for i, page in enumerate(reader.pages, start=1):
        frags.append(
            Fragment(
                anchor=f"{artifact}#p{i}",
                text=page.extract_text() or "",
                nature=nature,
                data={"pagina": i},
                artifact=artifact,
            )
        )
    return frags


def parse_json(artifact: str, path: Path) -> list[Fragment]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    nature = NATURE_BY_ARTIFACT.get(artifact, "especificacao")
    frags = [
        Fragment(
            anchor=f"{artifact}",
            text=json.dumps(data, ensure_ascii=False, indent=2),
            nature=nature,
            data=data,
            artifact=artifact,
        )
    ]
    # ensaios do configuracao.json ganham âncora própria (alimentam CHK-VERSOES)
    for ensaio in data.get("ensaios", []):
        if ensaio.get("ensaio_id"):
            frags.append(
                Fragment(
                    anchor=f"{artifact}#{ensaio['ensaio_id']}",
                    text=json.dumps(ensaio, ensure_ascii=False),
                    nature=nature,
                    data=ensaio,
                    artifact=artifact,
                )
            )
    return frags


def parse_project(project_path: Path) -> dict:
    """Pacote imutável → manifest + fragmentos + flags de divergência."""
    project_path = Path(project_path)
    files: list[dict] = []
    fragments: list[Fragment] = []
    flags: list[str] = []

    all_files = sorted(
        p for p in project_path.rglob("*") if p.is_file()
    )
    for p in all_files:
        rel = p.relative_to(project_path).as_posix()
        files.append({"path": rel, "sha256": _sha256(p), "bytes": p.stat().st_size})

    def parse_one(rel: str, p: Path) -> list[Fragment]:
        if rel.endswith(".csv"):
            return parse_csv(rel, p)
        if rel.endswith(".xlsx"):
            return parse_xlsx(rel, p)
        if rel.endswith(".pdf"):
            return parse_pdf(rel, p)
        if rel.endswith(".md"):
            return parse_md(rel, p)
        if rel.endswith(".json"):
            return parse_json(rel, p)
        return []

    # inventário primeiro (valida tipo pelo conteúdo)
    inv_path = project_path / "inventario_evidencias.csv"
    inv_rows: list[dict] = []
    if inv_path.exists():
        _, inv_rows = _read_csv(inv_path)

    for p in all_files:
        rel = p.relative_to(project_path).as_posix()
        if rel == "inventario_evidencias.csv":
            continue
        fragments.extend(parse_one(rel, p))

    # inventário também vira fragmentos (índice citável — T12)
    for row in inv_rows:
        anchor_key = row.get("id_evidencia")
        if not anchor_key:
            continue
        lines = [";".join(list(row.keys()))]
        lines.append(";".join("" if v is None else str(v) for v in row.values()))
        fragments.append(
            Fragment(
                anchor=f"inventario_evidencias.csv#{anchor_key}",
                text="\n".join(lines),
                nature="indice",
                data=row,
                artifact="inventario_evidencias.csv",
            )
        )

    # divergência inventário × pacote real = flag, não erro (spec 5.1)
    declared = {r["arquivo"] for r in inv_rows if r.get("arquivo")}
    present = {f["path"] for f in files}
    for missing in sorted(declared - present):
        flags.append(f"arquivo declarado no inventário ausente: {missing}")
    for extra in sorted(present - declared):
        flags.append(f"arquivo presente não declarado no inventário: {extra}")

    # conteúdo esperado × conteúdo real (T12: localizada ≠ comprovada)
    _expected_content = {
        "dossie_projeto.pdf": ["Pergunta registrada", "Contexto"],
        "registro_tecnico.pdf": ["Mecanismo", "comparação"],
        "transcricao_entrevista_tecnica.pdf": ["Entrevista"],
        "evidencias/metodo.md": ["Referência anterior", "Mecanismo"],
        "evidencias/cronologia.csv": ["evento"],
        "evidencias/medicoes.csv": ["ensaio"],
        "evidencias/resultados.csv": ["base_de_calculo"],
        "evidencias/configuracao.json": ["projeto_id"],
    }
    by_artifact: dict[str, str] = {}
    for f in fragments:
        by_artifact[f.artifact] = by_artifact.get(f.artifact, "") + "\n" + f.text
    for artifact, needles in _expected_content.items():
        if artifact not in by_artifact:
            continue
        for needle in needles:
            if needle.lower() not in by_artifact[artifact].lower():
                flags.append(f"conteúdo esperado ausente em {artifact}: '{needle}'")

    return {"manifest": {"files": files}, "fragments": fragments, "flags": flags}