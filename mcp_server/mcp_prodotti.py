"""MCP server — Prodotti, Listini, Prezzi."""
import sys

from mcp.server.fastmcp import FastMCP
from _common import _post, _search, _check_api_key

mcp = FastMCP("prodotti")


@mcp.tool()
def cerca_prodotti(testo: str = "", categoria: str = "", fornitore: str = "",
                   solo_attivi: bool = True, limit: int = 30) -> str:
    """Cerca prodotti per testo (codice/nome/descrizione), categoria o fornitore."""
    where = []
    if testo:
        where.append({"type": "or", "value": [
            {"type": "contains", "attribute": "name", "value": testo},
            {"type": "contains", "attribute": "codice", "value": testo},
            {"type": "contains", "attribute": "descrizioneEstesa", "value": testo},
        ]})
    if categoria:
        where.append({"type": "contains", "attribute": "categoria", "value": categoria})
    if fornitore:
        where.append({"type": "contains", "attribute": "accountName", "value": fornitore})
    if solo_attivi:
        where.append({"type": "isTrue", "attribute": "attivo"})
    if not where:
        where.append({"type": "isTrue", "attribute": "attivo"})

    prodotti = _search("CProdotto", where,
                       select="name,codice,categoria,descrizioneEstesa,prezzoListino,unitaMisura,accountName",
                       max_size=limit)
    if not prodotti:
        return f"Nessun prodotto trovato."
    lines = [f"📦 {len(prodotti)} prodotti:"]
    for p in prodotti:
        prezzo = p.get("prezzoListino")
        prezzo_str = f"€{float(prezzo):.2f}" if prezzo else "su richiesta"
        descr = (p.get("descrizioneEstesa") or "")[:80]
        lines.append(f"• [{p.get('codice','—')}] {p['name']} | {p.get('accountName','—')} | "
                     f"{p.get('categoria','—')} | {prezzo_str}/{p.get('unitaMisura','pz')}")
        if descr: lines.append(f"  {descr}")
    return "\n".join(lines)


@mcp.tool()
def lista_categorie_prodotti() -> str:
    """Elenca le categorie prodotti con conteggio."""
    prodotti = _search("CProdotto", [{"type": "isTrue", "attribute": "attivo"}],
                       select="categoria", max_size=5000)
    conteggio: dict = {}
    for p in prodotti:
        cat = p.get("categoria") or "Senza categoria"
        conteggio[cat] = conteggio.get(cat, 0) + 1
    if not conteggio:
        return "Nessun prodotto nel catalogo."
    return "📂 Categorie:\n" + "\n".join(
        f"  • {cat}: {n}" for cat, n in sorted(conteggio.items(), key=lambda x: -x[1]))


@mcp.tool()
def calcola_prezzo(nome_prodotto: str, quantita: int, nome_cliente: str = "") -> str:
    """Calcola il prezzo netto per un prodotto e quantità. Se indicato il cliente, usa il suo contratto."""
    prodotti = _search("CProdotto",
                       [{"type": "or", "value": [
                           {"type": "contains", "attribute": "name", "value": nome_prodotto},
                           {"type": "contains", "attribute": "codice", "value": nome_prodotto},
                       ]}],
                       select="id,name,codice,categoria,accountName,accountId,unitaMisura",
                       max_size=1)
    if not prodotti:
        return f"Prodotto '{nome_prodotto}' non trovato."
    p = prodotti[0]
    um = p.get("unitaMisura") or "pz"

    tipo_cliente = "rivenditore"
    sconto_pct = 0.0
    contratto_info = ""

    if nome_cliente:
        ac = _search("Account", [{"type": "contains", "attribute": "name", "value": nome_cliente}],
                     select="id,name", max_size=1)
        if ac:
            sconti = _search("CScontoCliente",
                             [{"type": "equals", "attribute": "accountId", "value": ac[0]["id"]},
                              {"type": "equals", "attribute": "fornitoreId", "value": p.get("accountId","")}],
                             select="tipoCliente,scontoPct,note", max_size=5)
            if sconti:
                s = sconti[0]
                tipo_cliente = s.get("tipoCliente") or "rivenditore"
                sconto_pct = float(s.get("scontoPct") or 0)
                contratto_info = f"Contratto: {tipo_cliente}" + (f" -{sconto_pct}%" if sconto_pct else "")
            else:
                contratto_info = f"⚠️ Nessun contratto per {ac[0]['name']} / {p.get('accountName','?')}"

    righe = _search("RigaListino",
                    [{"type": "equals", "attribute": "prodottoId", "value": p["id"]},
                     {"type": "equals", "attribute": "tipoCliente", "value": tipo_cliente}],
                    select="tipoCliente,quantitaMinima,prezzoNetto",
                    max_size=20)

    prezzo_base = None
    scaglione = 0
    for r in sorted(righe, key=lambda x: x.get("quantitaMinima", 0), reverse=True):
        if (r.get("quantitaMinima") or 0) <= quantita:
            prezzo_base = r.get("prezzoNetto")
            scaglione = r.get("quantitaMinima", 1)
            break

    if prezzo_base is None:
        tutti = _search("RigaListino",
                        [{"type": "equals", "attribute": "prodottoId", "value": p["id"]}],
                        select="tipoCliente,quantitaMinima,prezzoNetto", max_size=20)
        if tutti:
            scaglioni = "\n".join(
                f"  {r.get('tipoCliente','?')} qtà≥{r.get('quantitaMinima','?')}: €{r.get('prezzoNetto','?')}"
                for r in sorted(tutti, key=lambda x: (x.get("tipoCliente",""), x.get("quantitaMinima",0))))
            return f"Nessun prezzo {tipo_cliente} per qtà {quantita}.\nScaglioni:\n{scaglioni}"
        return f"Nessun prezzo in listino per '{p['name']}'."

    prezzo_finale = prezzo_base * (1 - sconto_pct / 100) if sconto_pct else prezzo_base
    totale = prezzo_finale * quantita

    lines = [
        f"📦 [{p.get('codice','—')}] {p['name']} × {quantita} {um}",
        f"   Fornitore: {p.get('accountName','—')} | {tipo_cliente} (qtà≥{scaglione})",
        f"   Prezzo netto: €{prezzo_base:.4f}/{um}",
    ]
    if contratto_info: lines.append(f"   {contratto_info}")
    if sconto_pct: lines.append(f"   Sconto extra: -{sconto_pct}% → €{prezzo_finale:.4f}/{um}")
    lines.append(f"   💰 Totale: €{totale:.2f}")
    return "\n".join(lines)


if __name__ == "__main__":
    _check_api_key()
    mcp.run(transport="stdio")
