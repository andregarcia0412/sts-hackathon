"""CHK-VERSOES — consistência cronologia ↔ medicoes ↔ configuracao.json + parâmetros não nulos."""
from __future__ import annotations

from ai_microservice.extraction.parsers import Fragment

# versões da cronologia que não alegam execução de ensaio
_NAO_EXECUCAO = {"documento-inicial", "protocolo-r1", "revisao-final"}


def run_chk_versoes(fragments: list[Fragment]) -> dict:
    cronologia_versoes: set[str] = set()
    for f in fragments:
        if f.artifact == "evidencias/cronologia.csv":
            v = f.data.get("versao")
            if v:
                cronologia_versoes.add(v)

    medicoes_versoes: set[str] = set()
    ensaios_por_versao: dict[str, set[str]] = {}
    for f in fragments:
        if f.artifact == "evidencias/medicoes.csv" and "registros" in f.data:
            for r in f.data["registros"]:
                v = r.get("versao")
                if v:
                    medicoes_versoes.add(v)
                    ensaios_por_versao.setdefault(v, set()).add(r.get("ensaio_id") or "")

    config: dict = {}
    for f in fragments:
        if f.artifact == "evidencias/configuracao.json" and f.data and "projeto_id" in f.data:
            config = f.data
            break
    config_versoes = set(config.get("versoes_registradas", []))
    config_ensaios = {e.get("ensaio_id"): e for e in config.get("ensaios", [])}

    # ensaios da cronologia (eventos de arquivamento) têm ensaio em medicoes?
    ensaios_med = {f.anchor.split("#")[1] for f in fragments if f.artifact == "evidencias/medicoes.csv"}

    parametros_nulos: list[str] = []
    for k, v in (config.get("parametros") or {}).items():
        if v is None:
            parametros_nulos.append(k)

    # versões de cronologia que ALEGAM execução (eventos de arquivamento) sem ensaio → inconsistência
    versoes_execucao = (
        cronologia_versoes - _NAO_EXECUCAO
    ) - medicoes_versoes
    consistentes = (
        bool(cronologia_versoes)
        and bool(medicoes_versoes)
        and not versoes_execucao
        and not parametros_nulos
    )

    return {
        "versoes_cronologia": sorted(cronologia_versoes),
        "versoes_medicoes": sorted(medicoes_versoes),
        "versoes_config": sorted(config_versoes),
        "versoes": sorted(cronologia_versoes | medicoes_versoes | config_versoes),
        "versoes_em_cronologia_sem_ensaio": sorted(versoes_execucao),
        "parametros_nulos": parametros_nulos,
        "ensaios_por_versao": {k: sorted(v) for k, v in ensaios_por_versao.items()},
        "consistentes": bool(consistentes),
    }