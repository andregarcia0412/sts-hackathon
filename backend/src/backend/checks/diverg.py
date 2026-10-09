"""CHK-DIVERG: numbers and claims of the interview × the results record (principle 6). Interviews carry planted
errors; this check makes sure a numeric divergence is never lost, as a candidate the sub-agents and the report see.

Four kinds, from the historical cases: a different number, the number of another version, another base
(percentage), and absence/totality of failures ("nenhuma leitura indevida" when a version had 2 of 8)."""

import re
import unicodedata

from backend.checks.data import cell, configuration, number, prose_number, rows
from backend.checks.falhas import direction
from backend.checks.models import CheckResult
from backend.extraction.schema import CanonicalProject, Fragment

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.;!?])\s+|\n+")  # "1.100" is a number, not the end of a sentence
TOKEN_RE = re.compile(r"(?<![\w.,])-?\d{1,3}(?:\.\d{3})+(?:,\d+)?|(?<![\w.,])-?\d+(?:[.,]\d+)?")
WORDS = {"um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6, "sete": 7,
         "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14, "catorze": 14,
         "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
         "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80, "noventa": 90, "cem": 100}
_NUM = r"(\d+(?:[.,]\d+)?|" + "|".join(sorted(WORDS, key=len, reverse=True)) + r")"
FRACTION_RE = re.compile(rf"\b{_NUM}\s*(?:/|d[oa]s|de)\s*{_NUM}\b", re.I)
TIME_UNIT_RE = re.compile(r"^\s*(?:s|ms|min|h|segundos?|minutos?|horas?|dias?|semanas?|mb|gb|kb)\b", re.I)
KEPT_RE = re.compile(r"\b(mantiv\w*|mante(?:ve|m)|mantid[oa]s?|sem alter\w*|n[ãa]o alter\w*|o mesmo|a mesma)\b", re.I)
PAIR_SUFFIXES = (("_inicial", "_final"), ("_antes", "_depois"), ("_v1", "_v2"), ("_original", "_ajustad"))
NONE_RE = re.compile(r"\b(nenhum[a]?|nunca|zero|sem (?:nenhum|qualquer))\b", re.I)
ALL_RE = re.compile(r"\b(tod[oa]s|sempre|100\s?%)\b", re.I)
SKIPPED_SECTIONS = {"cabecalho", "condicao_do_registro"}
CLOSE = 0.10  # a different number this close to a recorded one is a candidate (400 × 412), 4000 is not
CLOSE_PERCENT = 0.20


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z]{5,}", _plain(text))}


def _version_named(result: "_Result", plain_sentence: str) -> bool:
    """ "grafo restrito" names restrito-v4: the version without its -vN suffix appears in the sentence."""
    base = re.sub(r"-?v\d+$", "", _plain(result.version or ""))
    return bool(base) and len(base) >= 4 and base in plain_sentence


def _word_number(token: str) -> float | None:
    return float(WORDS[token.lower()]) if token.lower() in WORDS else prose_number(token)


def _is_year(value: float, token: str) -> bool:
    return value.is_integer() and 1990 <= value <= 2100 and "." not in token and "," not in token


class _Result:
    def __init__(self, row: Fragment) -> None:
        self.row = row
        self.version, self.metric = cell(row, "versao"), cell(row, "metrica")
        self.value, self.base = number(cell(row, "valor")), number(cell(row, "base_de_calculo"))
        self.rate = number(cell(row, "taxa_percentual"))
        self.stems = _stems(self.metric or "")


def _statement(sentence: str, result: _Result) -> str:
    return (f'A entrevista afirma "{sentence}"; o registro {result.row.alias} mostra "{result.row.text}"; '
            f"prevalece o registro, por ser primário e identificado por versão.")


def _candidate(kind: str, fragment: Fragment, sentence: str, result: _Result, said: str) -> dict:
    return {"tipo": kind, "depoimento_fragmento": fragment.id, "depoimento_trecho": sentence,
            "registro_fragmento": result.row.id, "registro_alias": result.row.alias, "registro_trecho": result.row.text,
            "afirmado": said, "registrado": f"{result.version}: {result.metric} = {cell(result.row, 'valor')}"
                                            f"/{cell(result.row, 'base_de_calculo')}",
            "frase": _statement(sentence, result)}


def _changed_parameters(canonical: CanonicalProject) -> list[tuple[str, object, object, Fragment]]:
    """(name, before, after, fragment) for parameter pairs recorded with different values (x_inicial ≠ x_final)."""
    parameters = configuration(canonical).get("parametros")
    fragment = next(iter(canonical.fragments_of("configuracao", "parametros")), None)
    if not isinstance(parameters, dict) or fragment is None:
        return []
    changed = []
    for key, before in parameters.items():
        for first, second in PAIR_SUFFIXES:
            if key.endswith(first):
                name = key[: -len(first)]
                after_key = next((k for k in parameters if k.startswith(name + second)), None)
                if after_key and parameters[after_key] != before:
                    changed.append((name, before, parameters[after_key], fragment))
    return changed


def _kept_parameter(sentence: str, changed: list, fragment: Fragment) -> list[dict]:
    """ "Mantivemos o limiar inicial" while the record shows the threshold changing from 3 to 5."""
    if not KEPT_RE.search(sentence):
        return []
    plain = _plain(sentence)
    found = []
    for name, before, after, record in changed:
        words = [w for w in re.split(r"[_\W]+", _plain(name)) if len(w) >= 4]
        if words and all(w[:5] in plain for w in words):
            found.append({
                "tipo": "parametro_mantido", "depoimento_fragmento": fragment.id, "depoimento_trecho": sentence,
                "registro_fragmento": record.id, "registro_alias": record.alias, "registro_trecho": record.text,
                "afirmado": KEPT_RE.search(sentence).group(0), "registrado": f"{name}: {before} → {after}",
                "frase": f'A entrevista afirma "{sentence}"; o registro {record.alias} mostra "{record.text}"; '
                         "prevalece o registro, por ser primário e identificado por versão."})
    return found


def find(canonical: CanonicalProject) -> list[dict]:
    results = [_Result(r) for r in rows(canonical, "resultados")]
    changed = _changed_parameters(canonical)
    if not results and not changed:
        return []
    versions = {r.version for r in results if r.version}
    candidates: list[dict] = []
    for fragment in canonical.fragments_of("entrevista"):
        if fragment.anchor in SKIPPED_SECTIONS:
            continue
        for sentence in (s.strip() for s in SENTENCE_SPLIT_RE.split(fragment.text)):
            if not sentence:
                continue
            candidates += _kept_parameter(sentence, changed, fragment)
            stems = _stems(sentence)
            related = [r for r in results if r.stems & stems or (r.version and r.version in sentence)]
            if not related:
                continue  # numbers about something the results do not measure (memory, sizes, windows)
            named = [v for v in versions if v in sentence]
            candidates += _fractions(sentence, related, fragment)
            candidates += _numbers(sentence, related, named, fragment)
            candidates += _absence_or_totality(sentence, related, fragment)
    unique = {(c["depoimento_trecho"], c["registro_fragmento"]): c for c in candidates}
    return list(unique.values())


def _fractions(sentence: str, results: list[_Result], fragment: Fragment) -> list[dict]:
    """ "um dos vinte replays" / "8 de 12": the same base recorded with another count."""
    found = []
    for match in FRACTION_RE.finditer(sentence):
        part, whole = _word_number(match.group(1)), _word_number(match.group(2))
        if part is None or whole is None or part > whole:
            continue
        same_base = [r for r in results if r.base == whole]
        if same_base and all(r.value != part for r in same_base):
            target = min(same_base, key=lambda r: abs((r.value or 0) - part))
            found.append(_candidate("numero_diferente", fragment, sentence, target, match.group(0)))
    return found


def _numbers(sentence: str, results: list[_Result], named: list[str], fragment: Fragment) -> list[dict]:
    found = []
    recorded = {n for r in results for n in (r.value, r.base, r.rate) if n is not None}
    fractions = [m.span() for m in FRACTION_RE.finditer(sentence)]
    for match in TOKEN_RE.finditer(sentence):
        if any(start <= match.start() < end for start, end in fractions):
            continue  # handled as a fraction
        if TIME_UNIT_RE.match(sentence[match.end():]):
            continue  # a duration or size, not a count of the results
        token = match.group(0)
        value = prose_number(token)
        if value is None or _is_year(value, token) or abs(value) < 3:
            continue
        percent = sentence[match.end():match.end() + 2].strip().startswith("%")
        if not percent and value in recorded:
            # the number of another version: said of version X, recorded for version Y of the same metric
            for version in named:
                own = [r for r in results if r.version == version]
                other = [r for r in results if r.version != version and value in (r.value, r.base)]
                if own and other and all(value not in (r.value, r.base) for r in own):
                    found.append(_candidate("numero_de_outra_versao", fragment, sentence, own[0], token))
            continue
        pool = [(r, r.rate) for r in results if r.rate is not None] if percent else \
            [(r, n) for r in results for n in (r.value, r.base) if n is not None]
        close = [(abs(value - n) / max(abs(n), 1e-9), r) for r, n in pool if n and value != n]
        limit = CLOSE_PERCENT if percent else CLOSE
        close = [(d, r) for d, r in close if d <= limit]
        if close:
            plain = _plain(sentence)
            _, result = min(close, key=lambda item: (not _version_named(item[1], plain), item[0]))
            kind = "base_ou_percentual" if percent else "numero_diferente"
            found.append(_candidate(kind, fragment, sentence, result, token + ("%" if percent else "")))
    return found


def _absence_or_totality(sentence: str, related: list[_Result], fragment: Fragment) -> list[dict]:
    found = []
    plain = _plain(sentence)
    named = [r for r in related if _version_named(r, plain)]
    related = named or related  # "a fila por dependência acertou todos" speaks of that version only
    if NONE_RE.search(sentence):
        for r in related:
            failed = (r.value or 0) > 0 if direction(r.metric) == "menor_e_melhor" else False
            if failed:
                found.append(_candidate("ausencia_de_falha", fragment, sentence, r, NONE_RE.search(sentence).group(0)))
    if ALL_RE.search(sentence):
        for r in related:
            if direction(r.metric) == "maior_e_melhor" and r.rate is not None and r.rate < 100:
                found.append(_candidate("totalidade", fragment, sentence, r, ALL_RE.search(sentence).group(0)))
    return found


def check(canonical: CanonicalProject) -> CheckResult:
    if not canonical.fragments_of("entrevista") or not (rows(canonical, "resultados") or _changed_parameters(canonical)):
        return CheckResult(id="CHK-DIVERG", status="nao_aplicavel", notes=["sem entrevista ou sem registro a comparar"])
    candidates = find(canonical)
    fragment_ids = list(dict.fromkeys(i for c in candidates for i in (c["depoimento_fragmento"], c["registro_fragmento"])))
    return CheckResult(id="CHK-DIVERG", status="alerta" if candidates else "ok",
                       facts={"divergencias": candidates}, fragment_ids=fragment_ids,
                       notes=["candidatas por comparação de números e de afirmações de ausência/totalidade; "
                              "o registro primário prevalece"])
