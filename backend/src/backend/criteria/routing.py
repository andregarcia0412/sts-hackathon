"""Which fragments each rule reads (catalog `roteamento`), so a sub-agent never sees the whole package."""

from dataclasses import dataclass, field

from backend.catalog.models import CatalogRule
from backend.extraction.schema import TABLE_TYPES, CanonicalProject, Fragment


@dataclass
class RoutedFragments:
    fragments: list[Fragment] = field(default_factory=list)
    testimony: list[Fragment] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)


def route_fragments(canonical: CanonicalProject, rules: list[CatalogRule], max_table_rows: int) -> RoutedFragments:
    wanted: list[tuple[str, str | None]] = []
    for rule in rules:
        for target in rule.roteamento:
            file_type, _, anchor = target.partition("#")
            if (file_type, anchor or None) not in wanted:
                wanted.append((file_type, anchor or None))
    routed = RoutedFragments()
    seen: set[str] = set()
    for file_type, anchor in wanted:
        selected = canonical.fragments_of(file_type, anchor)
        if file_type in TABLE_TYPES and len(selected) > max_table_rows:
            routed.truncated.append(f"{file_type}: {max_table_rows} de {len(selected)} linhas no prompt")
            selected = selected[:max_table_rows]
        for fragment in selected:
            if fragment.id not in seen and fragment.nature != "depoimento":
                seen.add(fragment.id)
                routed.fragments.append(fragment)
    routed.testimony = [f for f in canonical.fragments if f.nature == "depoimento"]
    return routed
