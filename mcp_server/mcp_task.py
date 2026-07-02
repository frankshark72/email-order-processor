"""MCP server — Task e attività pianificate."""
import sys
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP
from _common import _post, _search, _check_api_key

mcp = FastMCP("task")


@mcp.tool()
def crea_task(titolo: str, nome_cliente: str = "", scadenza: str = "",
              priorita: str = "Normal", nota: str = "") -> str:
    """Crea un task in EspoCRM. scadenza: YYYY-MM-DD. priorita: Low|Normal|High|Urgent."""
    due = scadenza or (date.today() + timedelta(days=1)).isoformat()
    payload: dict = {"name": titolo, "status": "Not Started",
                     "priority": priorita, "dateEnd": f"{due} 09:00:00"}
    if nota: payload["description"] = nota
    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id,name", max_size=1)
        if ac:
            payload["parentType"] = "Account"
            payload["parentId"] = ac[0]["id"]
    result = _post("Task", payload)
    return f"✅ Task '{titolo}' creato. Scadenza: {due}. ID: {result.get('id','?')}"


@mcp.tool()
def task_oggi() -> str:
    """Elenca i task in scadenza oggi o già scaduti (non completati)."""
    today = date.today().isoformat()
    where = [
        {"type": "or", "value": [
            {"type": "equals", "attribute": "dateEnd", "value": today},
            {"type": "before", "attribute": "dateEnd", "value": today},
        ]},
        {"type": "notEquals", "attribute": "status", "value": "Completed"},
    ]
    results = _search("Task", where,
                      select="name,status,dateEnd,parentName,priority", max_size=20)
    if not results:
        return "✅ Nessun task in scadenza oggi."
    lines = [f"📋 Task in scadenza ({len(results)}):"]
    for t in results:
        scad = t.get("dateEnd","")[:10]
        cliente = f" — {t['parentName']}" if t.get("parentName") else ""
        scaduto = " ⚠️SCADUTO" if scad < today else ""
        lines.append(f"• [{t.get('priority','Normal')}] {t['name']}{cliente} | {scad}{scaduto}")
    return "\n".join(lines)


@mcp.tool()
def lista_task(solo_aperti: bool = True, nome_cliente: str = "", limit: int = 20) -> str:
    """Elenca task. solo_aperti: esclude completati/cancellati."""
    where = []
    if solo_aperti:
        where.append({"type": "notIn", "attribute": "status", "value": ["Completed", "Canceled"]})
    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id", max_size=1)
        if ac:
            where.append({"type": "equals", "attribute": "parentId", "value": ac[0]["id"]})
    tasks = _search("Task", where,
                    select="name,status,priority,dateEnd,parentName", max_size=limit)
    if not tasks:
        return "Nessun task trovato."
    lines = [f"📋 Task ({len(tasks)}):"]
    for t in tasks:
        parent = f" | {t['parentName']}" if t.get("parentName") else ""
        lines.append(f"• [{t.get('priority','Normal')}] {t['name']} | "
                     f"{t.get('status','—')} | {(t.get('dateEnd','—'))[:10]}{parent}")
    return "\n".join(lines)


@mcp.tool()
def completa_task(titolo_o_id: str) -> str:
    """Segna un task come completato (cerca per titolo o ID)."""
    where = [{"type": "contains", "attribute": "name", "value": titolo_o_id}]
    tasks = _search("Task", where, select="id,name", max_size=1)
    if not tasks:
        return f"Task '{titolo_o_id}' non trovato."
    from _common import _patch
    _patch("Task", tasks[0]["id"], {"status": "Completed"})
    return f"✅ Task '{tasks[0]['name']}' completato."


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
