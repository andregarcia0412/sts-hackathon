"""`uv run backend-checks <benchmark_id>`: runs the deterministic checks over the canonical projects already saved
(zero tokens, no new extraction) and prints what each one found, plus the planted divergences recovered."""

import argparse
import asyncio
import json
from pathlib import Path

from beanie import PydanticObjectId

from backend.analyses.models import CanonicalRecord
from backend.benchmark.metrics import divergence_found
from backend.benchmark.models import Benchmark, DivergenceSnapshot
from backend.checks.divergences import check_divergences
from backend.checks.runner import run_checks
from backend.database import close_db, init_db

SUMMARY = {
    "CHK-RECALC": lambda f: f"não batendo {f.get('nao_batendo')} · vazio {f.get('vazio')}",
    "CHK-TEMPO": lambda f: f"inicial antes dos ensaios {f.get('documento_inicial_antes_dos_ensaios')} · "
                           f"vários anos {f.get('varios_anos_base')}",
    "CHK-VERSOES": lambda f: f"sem ensaio {f.get('versoes_sem_ensaio')} · nulos {f.get('parametros_nulos')}",
    "CHK-FALHAS": lambda f: f"versões {f.get('versoes_com_falha_ou_piora')} · pioras {len(f.get('pioras', []))}",
    "CHK-CONFIG": lambda f: f"referência {f.get('tipo_referencia_anterior')} · verbos {f.get('verbos_de_configuracao')}"
                            f" · faixa admitida {f.get('faixa_ja_admitida')} · algoritmo intacto "
                            f"{f.get('algoritmo_nao_modificado')}",
    "CHK-ESCOPO": lambda f: f"não executados {f.get('nao_executados')}",
    "CHK-DIVERG": lambda f: "; ".join(f"{d['tipo']}: “{d['afirmado']}” × {d['registrado']}"
                                      for d in f.get("divergencias", [])) or "-",
    "CHK-PERGUNTA": lambda f: "; ".join(f"[{q['marcador'] or '-'}] {q['pergunta']}" for q in f.get("perguntas", [])),
}


class _NoLLM:
    """Stands in for the LLM in the parser comparison: any agent call fails (and is counted)."""

    def __init__(self) -> None:
        self.calls = 0

    def model_for(self, role: str) -> str:
        return "none"

    async def structured(self, messages, schema, role="default"):
        self.calls += 1
        raise RuntimeError("no LLM in the parser comparison")


async def compare_parsers(benchmark: Benchmark, wanted: set[str]) -> None:
    """Deterministic mapping over the original files (GridFS) × the fragment ids of the saved canonical."""
    from backend.analyses.models import Analysis
    from backend.extraction.pipeline import extract_project
    from backend.projects.importer import IncomingFile
    from backend.projects.models import Project
    from backend.storage import read_file

    total_same = total = agent_files = files = 0
    seen = set()
    for run in benchmark.runs:
        if (wanted and run.code.upper() not in wanted) or run.code in seen:
            continue
        record = await CanonicalRecord.find_one(CanonicalRecord.analysis_id == run.analysis_id)
        analysis = await Analysis.get(PydanticObjectId(run.analysis_id))
        project = await Project.get(PydanticObjectId(analysis.project_id)) if analysis else None
        if record is None or project is None:
            continue
        seen.add(run.code)
        incoming = [IncomingFile(path=d.file_name, data=await read_file(d.gridfs_id), top_folder=project.code)
                    for d in project.active_documents()]
        llm = _NoLLM()
        fresh = await extract_project(llm, incoming, code_hint=project.code)
        saved = {f.id for f in record.canonical.fragments if f.file_type != "checagem"}
        new = {f.id for f in fresh.fragments}
        same = saved & new
        total_same, total = total_same + len(same), total + len(saved | new)
        by_agent = [f.path for f in fresh.files if f.mapping_source == "agente"]
        agent_files, files = agent_files + len(by_agent), files + len(fresh.files)
        print(f"{run.code}: {len(same)}/{len(saved | new)} fragmentos idênticos · arquivos pelo agente: "
              f"{', '.join(by_agent) or '-'}")
        for fid in sorted(saved - new):
            print(f"   só no canônico salvo (agente): {fid}")
        for fid in sorted(new - saved):
            print(f"   só no determinístico: {fid}")
    if total:
        print(f"\nFragmentos idênticos: {total_same}/{total} = {total_same / total:.1%} · "
              f"arquivos mapeados pelo agente: {agent_files}/{files}")


async def main_async(args: argparse.Namespace) -> None:
    await init_db()
    try:
        if args.parsers:
            benchmark = await Benchmark.get(PydanticObjectId(args.benchmark))
            await compare_parsers(benchmark, {c.upper() for c in args.projects})
            return
        benchmark = await Benchmark.get(PydanticObjectId(args.benchmark))
        if benchmark is None:
            raise SystemExit(f"benchmark not found: {args.benchmark}")
        wanted = {c.upper() for c in args.projects}
        found = planted = 0
        dump = {}
        seen = set()
        for run in benchmark.runs:
            if (wanted and run.code.upper() not in wanted) or run.code in seen:
                continue
            record = await CanonicalRecord.find_one(CanonicalRecord.analysis_id == run.analysis_id)
            if record is None:
                print(f"{run.code}: sem canônico salvo")
                continue
            seen.add(run.code)
            report = run_checks(record.canonical)
            dump[run.code] = report.model_dump(mode="json")
            print(f"\n== {run.code}")
            for check_id, result in report.results.items():
                detail = SUMMARY[check_id](result.facts) if result.status not in ("falhou", "nao_aplicavel") else \
                    "; ".join(result.notes)
                print(f"   {check_id:13} {result.status:13} {detail}")
            if case := benchmark.expected.get(run.code):
                divergences = [DivergenceSnapshot(criterion=d.criterion, testimony_quote=d.testimony_quote,
                                                  record_quote=d.record_quote, statement=d.statement)
                               for d in check_divergences(report)]
                for item in case.planted_divergences:
                    planted += 1
                    hit = divergence_found(item, divergences)
                    found += hit
                    print(f"   plantada: “{item.testimony}” × “{item.record}” → {'achada' if hit else 'NÃO achada'}")
        if planted:
            print(f"\nDivergências plantadas achadas pela CHK-DIVERG: {found}/{planted}")
        if args.out:
            args.out.write_text(json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")
    finally:
        await close_db()


def main() -> None:
    parser = argparse.ArgumentParser(description="Deterministic checks over saved canonical projects (zero tokens)")
    parser.add_argument("benchmark", help="benchmark id whose analyses have saved canonical projects")
    parser.add_argument("--projects", type=lambda v: [c.strip() for c in v.split(",") if c.strip()], default=[])
    parser.add_argument("--parsers", action="store_true",
                        help="compare the deterministic mapping (spec 05) with the saved canonical, zero tokens")
    parser.add_argument("--out", type=Path, help="also write every report as JSON (keep it outside the repo)")
    asyncio.run(main_async(parser.parse_args()))
