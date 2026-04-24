from contextlib import asynccontextmanager

from fastapi import FastAPI

from commands import COMMANDS, parse
from dog import connect_dog


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with connect_dog() as dog:
        app.state.dog = dog
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok", "dry_run": app.state.dog.dry_run}


@app.get("/api/debug")
async def debug():
    dog = app.state.dog
    conn = dog._conn
    info = {
        "dog_id": id(dog),
        "dry_run": dog.dry_run,
        "conn_present": conn is not None,
    }
    if conn is not None:
        info["is_connected"] = getattr(conn, "isConnected", None)
        info["conn_ip"] = getattr(conn, "ip", None)
        pc = getattr(conn, "pc", None)
        info["peer_connection_state"] = getattr(pc, "connectionState", None) if pc else None
        dc = getattr(conn, "datachannel", None)
        info["data_channel_state"] = getattr(getattr(dc, "channel", None), "readyState", None)
    return info


@app.get("/api/commands")
async def commands_list():
    return {"commands": sorted(COMMANDS.keys())}


@app.post("/api/move/{instructions}")
async def move(instructions: str):
    tokens = [t for t in instructions.split(",") if t.strip()]
    if not tokens:
        return {"status": "error", "message": "no commands given"}

    parsed = []
    for t in tokens:
        p = parse(t)
        if p is None:
            return {"status": "error", "message": f"unknown command: {t!r}"}
        parsed.append(p)

    dog = app.state.dog
    for name, arg in parsed:
        await COMMANDS[name](dog, arg)

    return {
        "status": "ok",
        "executed": [f"{n}{a if a is not None else ''}" for n, a in parsed],
        "dry_run": dog.dry_run,
    }
