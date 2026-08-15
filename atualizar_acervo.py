"""
VENUSTAS & TÍMPANO — Atualizador do Acervo
Busca esculturas de MÁRMORE em todo o Met Museum (qualquer região/época),
categoriza automaticamente e grava no arquivo acervo.json.

- Só adiciona IDs novos (não duplica o que já existe no acervo.json)
- Roda sozinho toda semana via GitHub Actions, OU manualmente:
    python atualizar_acervo.py

Sem dependências externas — usa só a biblioteca padrão do Python.
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse

# ── CONFIGURAÇÃO ──────────────────────────────────────────
ARQUIVO   = "acervo.json"
DELAY     = 0.25
MAX_NOVOS = 40          # quantas esculturas novas adicionar por execução
MAX_VERIFICAR = 400     # teto de objetos a verificar por execução (evita rodar demais)

MET = "https://collectionapi.metmuseum.org/public/collection/v1"

# Termos de busca — mármore de qualquer departamento
BUSCAS = [
    "marble statue", "marble bust", "marble head", "marble figure",
    "marble relief", "marble torso", "marble sculpture", "marble goddess",
    "marble angel", "marble sarcophagus", "marble portrait", "marble nymph",
    "marble venus", "marble apollo", "marble madonna",
]

# ── CATEGORIZAÇÃO AUTOMÁTICA ──────────────────────────────
# ordem importa: a primeira que casar vence
REGRAS_CATEGORIA = [
    ("anjos",      ["angel", "cherub", "putto", "seraph"]),
    ("deusas",     ["venus", "aphrodite", "athena", "minerva", "juno", "hera",
                    "diana", "artemis", "goddess", "nymph", "muse", "grace",
                    "madonna", "virgin", "maria"]),
    ("deuses",     ["apollo", "zeus", "jupiter", "hermes", "mercury", "dionysos",
                    "bacchus", "hercules", "herakles", "mars", "ares", "god",
                    "eros", "cupid", "satyr", "faun"]),
    ("atletas",    ["athlete", "discobolus", "wrestler", "boxer", "runner"]),
    ("bustos",     ["bust", "portrait bust"]),
    ("cabecas",    ["head", "mask"]),
    ("relevos",    ["relief", "stele", "plaque", "frieze"]),
    ("sarcofagos", ["sarcophagus", "sarcophagi", "tomb", "grave"]),
    ("figuras",    ["statue", "statuette", "figure", "figurine", "torso",
                    "kouros", "kore", "sculpture"]),
]

def categorizar(obj):
    texto = " ".join([
        obj.get("title",""), obj.get("objectName",""),
        obj.get("classification",""),
    ]).lower()
    for nome, palavras in REGRAS_CATEGORIA:
        for p in palavras:
            if p in texto:
                return nome
    return "figuras"  # padrão

# ── FILTRO: é escultura de mármore? ───────────────────────
EXCLUIR = [
    "vase","vessel","bowl","cup","lamp","coin","gem","ring","fragment",
    "earring","necklace","bracelet","mirror","fibula","furniture",
    "table","chair","fireplace","mantel","chimneypiece","fountain",
    "column","capital","cinerary","urn","altar","basin","font",
    "inlay","tile","mosaic","intarsia","architectural","cornice",
]

def eh_marmore_escultura(obj):
    medium = (obj.get("medium") or "").lower()
    if "marble" not in medium:
        return False
    texto = " ".join([
        obj.get("title",""), obj.get("objectName",""),
        obj.get("classification",""),
    ]).lower()
    for ex in EXCLUIR:
        if ex in texto:
            return False
    return True

# ── CORES ─────────────────────────────────────────────────
def cor(t,c): return f"\033[{c}m{t}\033[0m"
VERDE   = lambda t: cor(t,"92")
CINZA   = lambda t: cor(t,"90")
AMARELO = lambda t: cor(t,"93")
VERMELHO= lambda t: cor(t,"91")
NEGRITO = lambda t: cor(t,"1")

# ── MET API ───────────────────────────────────────────────
def buscar_ids(query):
    # sem departmentId = busca no acervo inteiro
    url = f"{MET}/search?hasImages=true&q={urllib.parse.quote(query)}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read())
        return data.get("objectIDs") or []
    except Exception as e:
        print(CINZA(f"  [aviso] '{query}': {e}"))
        return []

def buscar_objeto(obj_id):
    try:
        with urllib.request.urlopen(f"{MET}/objects/{obj_id}", timeout=20) as r:
            return json.loads(r.read())
    except:
        return None

# ── ARQUIVO ───────────────────────────────────────────────
def carregar_acervo():
    if not os.path.exists(ARQUIVO):
        return {
            "gerado_em": "",
            "fonte": "The Metropolitan Museum of Art (CC0)",
            "categorias": [c[0] for c in REGRAS_CATEGORIA],
            "esculturas": []
        }
    with open(ARQUIVO, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_acervo(acervo):
    acervo["gerado_em"] = time.strftime("%Y-%m-%d")
    acervo["categorias"] = [c[0] for c in REGRAS_CATEGORIA]
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(acervo, f, ensure_ascii=False, indent=2)

def barra(atual, total, txt=""):
    if total == 0: return
    b = "█"*int(atual/total*24) + "░"*(24-int(atual/total*24))
    print(f"\r  [{b}] {atual}/{total}  {CINZA(txt[:32])}", end="", flush=True)

# ════════════════════════════════════════════════════════════
def main():
    print()
    print(NEGRITO("  VENUSTAS & TÍMPANO — Atualizar Acervo (mármore)"))
    print()

    acervo = carregar_acervo()
    ja_tem = set(e["met_id"] for e in acervo["esculturas"])
    print(f"  Acervo atual: {len(ja_tem)} esculturas")
    print()

    # 1. Coletar candidatos
    print(AMARELO("  Buscando mármore no Met (acervo inteiro)..."))
    candidatos = []
    vistos = set()
    for q in BUSCAS:
        ids = buscar_ids(q)
        novos = [i for i in ids if i not in vistos and i not in ja_tem]
        vistos.update(ids)
        candidatos.extend(novos)
        print(f"  → {q:<20} {len(novos)} novos")
        time.sleep(DELAY)

    candidatos = list(dict.fromkeys(candidatos))[:MAX_VERIFICAR]
    print(f"\n  {len(candidatos)} candidatos a verificar")
    print()

    if not candidatos:
        print(VERDE("  ✓ Nada novo — acervo já atualizado."))
        salvar_acervo(acervo)  # atualiza a data
        return

    # 2. Verificar e adicionar
    print(AMARELO("  Filtrando mármore e categorizando..."))
    print()
    adicionados = 0
    por_categoria = {}

    for i, obj_id in enumerate(candidatos):
        if adicionados >= MAX_NOVOS:
            break
        obj = buscar_objeto(obj_id)
        time.sleep(DELAY)
        if not obj:
            continue
        if not eh_marmore_escultura(obj):
            continue
        if not obj.get("primaryImageSmall"):
            continue

        cat = categorizar(obj)
        acervo["esculturas"].append({
            "met_id":      obj["objectID"],
            "titulo":      obj.get("title") or "Sem título",
            "artista":     obj.get("artistDisplayName") or "Desconhecido",
            "data_obj":    obj.get("objectDate") or "",
            "material":    obj.get("medium") or "",
            "tipo":        obj.get("objectName") or "",
            "categoria":   cat,
            "thumb":       obj.get("primaryImageSmall"),
            "imagem_full": obj.get("primaryImage") or obj.get("primaryImageSmall"),
            "n_angulos":   1 + len(obj.get("additionalImages") or []),
            "object_url":  obj.get("objectURL") or "",
        })
        adicionados += 1
        por_categoria[cat] = por_categoria.get(cat, 0) + 1
        barra(adicionados, min(MAX_NOVOS, len(candidatos)), obj.get("title",""))

    print()
    print()

    # 3. Salvar
    salvar_acervo(acervo)
    total = len(acervo["esculturas"])
    print(VERDE(f"  ✓ {adicionados} novas adicionadas"))
    for cat, n in sorted(por_categoria.items()):
        print(CINZA(f"      {cat}: +{n}"))
    print(NEGRITO(f"  ► Acervo total agora: {total} esculturas"))
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Interrompido.")
        sys.exit(0)
