from beanie import Document

from backend.analyses.models import Analysis, Batch, CanonicalRecord
from backend.assistant.norms import NormChunkDocument
from backend.catalog.models import RuleDocument
from backend.graph.models import GraphEdge, GraphNode
from backend.projects.models import Project
from backend.review.models import Contestation, Decision, EvidenceReview, RuleDecision
from backend.search.cache import SearchCacheEntry
from backend.users.models import User

# Register every Beanie Document here so init_beanie picks it up.
DOCUMENT_MODELS: list[type[Document]] = [
    User, RuleDocument, SearchCacheEntry, Project, GraphNode, GraphEdge, Analysis, CanonicalRecord, Batch,
    Decision, Contestation, RuleDecision, EvidenceReview, NormChunkDocument,
]
