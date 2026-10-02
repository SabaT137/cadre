import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.api.routes import admin, auth, chat, finance, integrations, templates
from app.bootstrap import bootstrap
from app.config import get_settings
from app.graph.builder import build_graph
from app.services.template_store import get_store

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    s.checkpoint_db.parent.mkdir(parents=True, exist_ok=True)
    get_store()  # registers the bundled contract template
    await bootstrap()
    async with AsyncSqliteSaver.from_conn_string(str(s.checkpoint_db)) as saver:
        app.state.graph = build_graph(checkpointer=saver)
        yield


app = FastAPI(title="Stixor Office Multi-Agent API", version="0.2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (auth, chat, templates, finance, integrations, admin):
    app.include_router(r.router)


@app.get("/health", tags=["meta"])
def health():
    s = get_settings()
    return {
        "status": "ok",
        "supervisor_model": s.supervisor_model,
        "worker_model": s.worker_model,
        "worker_native_tools": s.worker_native_tools,
    }
