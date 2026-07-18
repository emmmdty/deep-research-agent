"""FastAPI routers for the authenticated product surface."""

from deep_research_agent.gateway.routes import admin, auth, chat, corpus, memory, runs, topics

PRODUCT_ROUTERS = (
    auth.router,
    chat.router,
    topics.router,
    runs.router,
    corpus.router,
    memory.router,
    admin.router,
)

__all__ = ["PRODUCT_ROUTERS"]
