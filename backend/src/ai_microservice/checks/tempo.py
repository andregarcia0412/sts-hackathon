"""CHK-TEMPO — linha do tempo, data de referência, ordem hipótese→ensaios, datas progressivas."""
from __future__ import annotations

from ai_microservice.extraction.parsers import Fragment


def run_chk_tempo(fragments: list[Fragment]) -> dict:
    eventos: list[dict] = []
    for f in fragments:
        if f.artifact == "evidencias/cronologia.csv":
            eventos.append(f.data)
    eventos.sort(key=lambda e: str(e.get("data") or ""))
    if not eventos:
        return {"data_referencia": None, "eventos": [], "ordem_ok": None, "progressivas_ok": None}

    data_ref = eventos[0].get("data")
    datas = [e.get("data") for e in eventos]

    # ordem: documento-inicial (registro do problema/referências) antes dos ensaios
    idx_inicial = next(
        (i for i, e in enumerate(eventos) if str(e.get("versao") or "") == "documento-inicial"),
        None,
    )
    idx_ensaios = [
        i for i, e in enumerate(eventos)
        if str(e.get("evento") or "").lower().startswith("arquivamento")
    ]
    ordem_ok: bool | None = None
    if idx_inicial is not None and idx_ensaios:
        ordem_ok = all(idx_inicial < i for i in idx_ensaios)
    elif idx_inicial is not None:
        ordem_ok = True

    # datas progressivas (T5: contemporâneo > reconstruído) — sem dois eventos na mesma data final
    progressivas_ok = len(datas) == len(set(datas)) and datas == sorted(datas)

    # flag T2: cronologia atravessa mais de um ano-base?
    anos = {str(d)[:4] for d in datas if d}
    t2_flag = len(anos) > 1

    return {
        "data_referencia": data_ref,
        "data_final": datas[-1],
        "eventos": eventos,
        "ordem_ok": ordem_ok,
        "progressivas_ok": progressivas_ok,
        "t2_plurianual_flag": t2_flag,
    }