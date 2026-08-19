"""Dagster resources: the dependency injection for this layer.

~40 lines, matching what dbt's manifest and DI containers replaced --
Dagster resources are the dependency injection now (architecture §2).
"""

from dagster import ConfigurableResource
from dagster_dlt import DagsterDltResource

from lib import db as db_module
from lib.embedding import embed


class DbResource(ConfigurableResource):
    """Exposes lib.db's module-level functions as an injectable resource."""

    def upsert_chunks(
        self, chunks: list[dict], embeddings: list[list[float]], *, embedder_model_id: str
    ) -> None:
        """See lib.db.upsert_chunks."""
        db_module.upsert_chunks(chunks, embeddings, embedder_model_id=embedder_model_id)

    def log_run(self, **kwargs) -> None:
        """See lib.db.log_run."""
        db_module.log_run(**kwargs)

    def finish_run(self, **kwargs) -> None:
        """See lib.db.finish_run."""
        db_module.finish_run(**kwargs)

    def record_violation(self, **kwargs) -> None:
        """See lib.db.record_violation."""
        db_module.record_violation(**kwargs)


class EmbedderResource(ConfigurableResource):
    """Wraps the fastembed model behind an injectable resource."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """See lib.embedding.embed."""
        return embed(texts)


dlt_resource = DagsterDltResource()
db_resource = DbResource()
embedder_resource = EmbedderResource()
