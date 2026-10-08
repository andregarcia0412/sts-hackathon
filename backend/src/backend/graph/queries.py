from backend.graph.models import EdgeData, GraphEdge, GraphNode, NodeData


async def save_graph(analysis_id: str, nodes: list[NodeData], edges: list[EdgeData]) -> None:
    """Writes the graph of one analysis. Re-saving the same analysis replaces it (idempotent)."""
    await GraphNode.find(GraphNode.analysis_id == analysis_id).delete()
    await GraphEdge.find(GraphEdge.analysis_id == analysis_id).delete()
    if nodes:
        await GraphNode.insert_many([GraphNode(**n.model_dump()) for n in nodes])
    if edges:
        await GraphEdge.insert_many([GraphEdge(**e.model_dump()) for e in edges])


async def trace(analysis_id: str, node_id: str) -> list[GraphNode]:
    """Every node that supports `node_id`, walking edges backwards with $graphLookup (class → … → sources)."""
    pipeline = [
        {"$match": {"analysis_id": analysis_id, "node_id": node_id}},
        {
            "$graphLookup": {
                "from": GraphEdge.Settings.name,
                "startWith": "$node_id",
                "connectFromField": "source",
                "connectToField": "target",
                "as": "edges",
                "restrictSearchWithMatch": {"analysis_id": analysis_id},
            }
        },
    ]
    rows = await GraphNode.aggregate(pipeline).to_list()
    if not rows:
        return []
    reached = {edge["source"] for edge in rows[0]["edges"]} | {edge["target"] for edge in rows[0]["edges"]}
    # sources are reached through "cita" edges that point away from the evidence: follow them too
    evidence_ids = [n for n in reached if n.startswith("evidence:") or n.startswith("divergence:") or n.startswith("gap:")]
    cited = await GraphEdge.find({"analysis_id": analysis_id, "source": {"$in": evidence_ids}}).to_list()
    reached |= {edge.target for edge in cited}
    return await GraphNode.find({"analysis_id": analysis_id, "node_id": {"$in": sorted(reached)}}).to_list()
