"""Grounding of web queries in the project's domain (spec 10): a query with none of the project's own technical
terms is dropped before it leaves the machine (no "Internet of Things Wikipedia", no literal "NOV-W3").

Terms come from the canonical project only (new element, barrier, mechanism §2, metric names, generic keywords),
never from an LLM answer. They are a reference list, never sent anywhere; still, project codes, internal codes,
numbers and sensitive terms are kept out (T6)."""

import re
import unicodedata

from backend.extraction.schema import CanonicalProject
from backend.search.sanitize import sanitize_query

STEM = 5
ACRONYM_RE = re.compile(r"\b[A-Z][A-Z0-9]{1,5}\b")  # RAG, MFA, SDK, OCR... as written in the project
WORD_RE = re.compile(r"[a-z][a-z0-9_]{3,}")  # 4+ letters: "lote", "fila", "tcp"... are domain words too
STOPWORDS = {
    "sobre", "entre", "quando", "porque", "foram", "sendo", "estes", "estas", "essas", "esses", "outro", "outra",
    "mesmo", "mesma", "ainda", "apenas", "antes", "depois", "durante", "todas", "todos", "cada", "nesse", "nessa",
    "deste", "desta", "pelos", "pelas", "uma", "para", "como", "mais", "menos", "seção", "secao", "versao", "versoes",
    "valor", "valores", "registro", "registros", "projeto", "equipe", "documento", "arquivo", "arquivos",
    "which", "where", "there", "their", "about", "using", "based", "these", "those", "other", "after", "before",
    "between", "without", "within", "patent", "paper", "study", "method", "system", "systems", "approach",
    "with", "from", "that", "this", "than", "into", "over", "under", "uses", "pelo", "pela", "isso", "esse", "essa",
    "este", "esta", "mais", "pode", "sido", "ser", "dos", "das", "nos", "nas", "sem", "com", "por", "que",
    "guide", "solutions", "solution", "tool", "tools", "best", "practices",
}
# The project is written in Portuguese and the queries are mostly in English: common technical words of the package
# and their English stems, so "batch" grounds in a project that says "lote".
GLOSSARY = {
    "lote": ("batch",), "fila": ("queue",), "janela": ("window",), "limiar": ("threshold",), "reexec": ("retry",),
    "repet": ("retry", "repeat"), "falha": ("failure", "fault"), "carga": ("load",), "atraso": ("delay", "latency"),
    "laten": ("latency",), "conex": ("connection",), "mensa": ("message",), "duplic": ("duplicate", "dedup"),
    "chave": ("key",), "sessa": ("session",), "conci": ("reconciliation", "matching"), "regis": ("record", "log"),
    "regra": ("rule",), "alert": ("alert",), "fraud": ("fraud",), "golpe": ("fraud", "scam"), "conta": ("account",),
    "trans": ("transaction",), "sincr": ("sync",), "mescl": ("merge",), "conflito": ("conflict",),
    "consen": ("consent",), "crédi": ("credit",), "credi": ("credit",), "polit": ("policy",), "motor": ("engine",),
    "docum": ("document",), "leitu": ("reading", "ocr"), "cifra": ("encrypt", "cipher"), "crypt": ("crypto",),
    "autent": ("authentication", "auth"), "dispo": ("device",), "apare": ("device", "mobile"), "camer": ("camera",),
    "offli": ("offline",), "rede": ("network",), "servi": ("service",), "gatew": ("gateway",), "rota": ("route",),
    "versa": ("version",), "migra": ("migration",), "sonda": ("probe", "monitoring"), "agenc": ("branch", "agency"),
    "monit": ("monitoring",), "simul": ("simulation",), "ataqu": ("attack",), "expli": ("explanation",),
    "audit": ("audit",), "cofre": ("vault",), "norma": ("normalization",), "cadas": ("registry",),
    "trafeg": ("traffic",), "trafego": ("traffic",), "manuten": ("maintenance",), "biometr": ("biometric",),
    "multifator": ("mfa", "multi"), "recupera": ("recovery",), "dispositivo": ("device",), "presenca": ("liveness",),
    "painel": ("dashboard",), "canal": ("channel",), "canais": ("channel",), "autoriz": ("authorization",),
    "permiss": ("permission", "authorization"), "estado": ("state",), "consist": ("consistency",), "ordem": ("order", "ordering"), "grafo": ("graph",), "aresta": ("edge",),
}
# Words of any search that say nothing about the project ("open problem", "error correction"...).
GENERIC_QUERY_WORDS = {"patent", "patents", "paper", "papers", "survey", "review", "study", "documentation", "open",
                       "problem", "problems", "error", "errors", "correction", "issue", "issues", "challenge",
                       "challenges", "limitation", "limitations", "state", "art", "wikipedia", "overview",
                       "introduction", "definition", "example", "examples", "general", "standard", "standards"}


def _plain(text: str) -> str:
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()


def _stems(text: str) -> set[str]:
    return {w[:STEM] for w in WORD_RE.findall(_plain(text)) if w not in STOPWORDS and not any(c.isdigit() for c in w)}


def domain_terms(canonical: CanonicalProject) -> set[str]:
    """Stems (first 5 letters, no accents) of the project's own technical vocabulary."""
    ctx = canonical.context
    texts = [ctx.title or "", ctx.elemento_novo.text or "", ctx.barreira.text or "", ctx.referencia_anterior.text or "",
             ctx.pergunta.text or "", *ctx.palavras_chave_pt, *ctx.palavras_chave_en, *ctx.produtos_citados]
    texts += [f.text for section in ("1", "2", "3") for f in canonical.fragments_of("metodo", section)]
    texts += [f.text for key in ("contexto", "pergunta_registrada") for f in canonical.fragments_of("dossie", key)]
    texts += [(f.data or {}).get("metrica") or "" for f in canonical.fragments
              if f.file_type in ("medicoes", "resultados")]
    clean = sanitize_query(" ".join(texts), ctx.termos_sensiveis).sanitized  # no codes, numbers or sensitive names
    stems = _stems(clean)
    stems |= {a.lower() for a in ACRONYM_RE.findall(clean) if not any(c.isdigit() for c in a)}
    plain_text = _plain(clean)
    for portuguese, english in GLOSSARY.items():
        if _plain(portuguese) in plain_text:
            stems |= {word[:STEM] for word in english}
    return stems


def grounded(query: str, terms: set[str]) -> bool:
    """True when the query shares at least one technical stem with the project (an empty list never blocks)."""
    if not terms:
        return True
    words = {w[:STEM] for w in WORD_RE.findall(_plain(query))
             if w not in STOPWORDS and w not in GENERIC_QUERY_WORDS and not any(c.isdigit() for c in w)}
    words |= {a.lower() for a in ACRONYM_RE.findall(query) if a.lower() not in {"trl", "api", "url", "faq"}}
    return bool(words & terms)
