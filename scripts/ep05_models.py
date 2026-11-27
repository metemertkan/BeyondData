"""Episode 5: the weight ladder, made from Ollama's own fp16 file, and what the "number on the box" says.

    uv run python -m scripts.ep05_models --ladder     # llama-quantize fp16 -> each level, then `ollama create`
    uv run python -m scripts.ep05_models --readback   # what each model is, read back from Ollama and the files
    uv run python -m scripts.ep05_models --kld        # KL divergence and same-top-token against fp16 on the passages
    uv run python -m scripts.ep05_models --tensors    # each file's tensor types (results/ep05/tensors.json)

Ollama's library has three versions of qwen3:8b: fp16, q8_0 and q4_K_M (the default tag). The other levels
people choose from (Q6_K, Q5_K_M, Q3_K_M, Q2_K) are made here from the same fp16 file with llama.cpp's
llama-quantize, static (no importance matrix), the way `ollama create --quantize` makes them. Q8_0 and Q4_K_M
are also made, to check whether Ollama's files are the same static quantization. They aren't: Ollama's keep
attn_v in F16 (PLAN §6, amendment 1), so Q4_K_M made here is imported too and run as its own design.
Each made file is imported with qwen3:8b's own template and parameters, so only the weights differ.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

from quant import llm

ROOT = Path(__file__).resolve().parent.parent
GGUF = ROOT / "data" / "ep05" / "gguf"
OUT = ROOT / "results" / "ep05"
COMPOSE = ["docker", "compose", "-f", str(ROOT / "docker-compose.ep05.yml")]
MADE = ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q3_K_M", "Q2_K"]
LIBRARY = {"F16": "qwen3:8b-fp16", "Q8_0": "qwen3:8b-q8_0", "Q4_K_M": "qwen3:8b"}
IMPORT_ALSO = {"Q4_K_M"}      # made here and in the library: both are run (amendment 1)


def made_tag(q: str) -> str:
    return f"bd5/qwen3-8b:{q.lower()}"


def sh(cmd: list[str], **kw) -> str:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kw).stdout


def blob(model: str) -> str:
    """The GGUF blob behind an Ollama model, as a path inside the containers (/root/.ollama or /models)."""
    mf = sh(["docker", "exec", "bd5-ollama", "ollama", "show", "--modelfile", model])
    return re.search(r"^FROM (\S+)", mf, re.M).group(1)


def tools(*args: str) -> str:
    return sh(COMPOSE + ["--profile", "tools", "run", "--rm", "--entrypoint", args[0], "llamacpp", *args[1:]])


def modelfile(gguf_in_container: str) -> str:
    mf = sh(["docker", "exec", "bd5-ollama", "ollama", "show", "--modelfile", "qwen3:8b"])
    return re.sub(r"^FROM \S+", f"FROM {gguf_in_container}", mf, count=1, flags=re.M)


def ladder() -> None:
    GGUF.mkdir(parents=True, exist_ok=True)
    fp16 = blob(LIBRARY["F16"]).replace("/root/.ollama", "/models")
    for q in MADE:
        out = GGUF / f"qwen3-8b-{q.lower()}.gguf"
        if not out.exists():
            tools("/app/llama-quantize", fp16, f"/gguf/{out.name}", q)
        if q in LIBRARY and q not in IMPORT_ALSO:   # Ollama has its own file at this level: compare only
            continue
        (GGUF / f"Modelfile.{q.lower()}").write_text(modelfile(f"/gguf/{out.name}"))
        sh(["docker", "exec", "bd5-ollama", "ollama", "create", made_tag(q), "-f", f"/gguf/Modelfile.{q.lower()}"])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 24), b""):
            h.update(chunk)
    return h.hexdigest()


def readback() -> dict:
    rows = {}
    made = [(q if q not in LIBRARY else f"{q} (made here)", made_tag(q)) for q in MADE if q not in LIBRARY or q in IMPORT_ALSO]
    for q, tag in [*LIBRARY.items(), *made]:
        s = llm.show(tag)
        b = blob(tag)
        rows[q] = {"model": tag, "source": "Ollama library" if tag in LIBRARY.values() else "llama-quantize from Ollama's fp16",
                   "quantization_level": s["details"].get("quantization_level"),
                   "parameter_size": s["details"].get("parameter_size"), "blob": b.rsplit("/", 1)[-1]}
    # Ollama's Q8_0 / Q4_K_M against the same level made here from its fp16: same bytes?
    for q in ("Q8_0", "Q4_K_M"):
        mine = GGUF / f"qwen3-8b-{q.lower()}.gguf"
        if mine.exists():
            rows[q]["made_here_sha256"] = sha256(mine)
            rows[q]["made_here_bytes"] = mine.stat().st_size
            rows[q]["same_as_made_here"] = rows[q]["blob"] == f"sha256-{rows[q]['made_here_sha256']}"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "models.json").write_text(json.dumps(rows, indent=1))
    print(json.dumps(rows, indent=1))
    return rows


KLD_TOKENS_WORDS = 15_000      # about 20,000 tokens: 39 chunks of 512


def kld_text() -> Path:
    """The test questions' passages (what rag reads), once each, until about 20,000 tokens."""
    from quant import tasks
    t = tasks.load("full")
    seen, words, parts = set(), 0, []
    for q in t["nq"]:
        for p in q["rag"]:
            key = p["title"] + p["text"][:80]
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"{p['title']}\n{p['text']}")
            words += len(p["text"].split())
        if words >= KLD_TOKENS_WORDS:
            break
    path = GGUF / "kld_text.txt"
    path.write_text("\n\n".join(parts))
    return path


def parse_kld(out: str) -> dict:
    grab = lambda pat: (lambda m: float(m.group(1)) if m else None)(re.search(pat, out))
    return {"ppl_q": grab(r"Mean PPL\(Q\)\s*:\s*([\d.]+)"), "ppl_base": grab(r"Mean PPL\(base\)\s*:\s*([\d.]+)"),
            "kld_mean": grab(r"Mean\s+KLD:\s*([\d.]+)"), "kld_p99": grab(r"99\.0%\s+KLD:\s*([\d.]+)"),
            "same_top_p": grab(r"Same top p:\s*([\d.]+)")}


def kld() -> dict:
    """KL divergence and same-top-token rate against fp16 (llama-perplexity, 512-token chunks)."""
    kld_text()
    base = "/gguf/kld_base.bin"
    fp16 = blob(LIBRARY["F16"]).replace("/root/.ollama", "/models")
    if not (GGUF / "kld_base.bin").exists():
        tools("/app/llama-perplexity", "-m", fp16, "-f", "/gguf/kld_text.txt", "-c", "512", "-t", "12",
              "--kl-divergence-base", base)
    res = {}
    for q in ["Q8_0", "Q6_K", "Q5_K_M", "Q4_K_M", "Q4_K_M (made here)", "Q3_K_M", "Q2_K"]:
        level = q.split()[0]
        model = (blob(LIBRARY[q]).replace("/root/.ollama", "/models") if q in LIBRARY
                 else f"/gguf/qwen3-8b-{level.lower()}.gguf")
        r = subprocess.run(COMPOSE + ["--profile", "tools", "run", "--rm", "--entrypoint", "/app/llama-perplexity",
                                      "llamacpp", "-m", model, "-c", "512", "-t", "12", "--kl-divergence-base", base,
                                      "--kl-divergence"], text=True, capture_output=True, check=True)
        res[q] = parse_kld(r.stdout + r.stderr)
        print(q, res[q], flush=True)
    (OUT / "kld.json").write_text(json.dumps(res, indent=1))
    return res


TENSOR_TYPES = """
import collections, json, sys, gguf
out = {}
for name, path in zip(sys.argv[1::2], sys.argv[2::2]):
    r = gguf.GGUFReader(path)
    kinds = collections.defaultdict(collections.Counter)
    for t in r.tensors:
        kinds[t.name.split(".", 2)[-1] if t.name.startswith("blk.") else t.name][t.tensor_type.name] += 1
    out[name] = {k: dict(v) for k, v in sorted(kinds.items())}
print(json.dumps(out))
"""


def tensors() -> dict:
    """Each file's tensor types, grouped by tensor (blk.N. stripped), read from the GGUF headers in the tools image."""
    args = []
    for q, tag in [*LIBRARY.items(), *[(f"{q} (made here)", made_tag(q)) for q in MADE if q != "Q8_0"]]:
        args += [q, blob(tag).replace("/root/.ollama", "/models")]
    args += ["Q8_0 (made here)", "/gguf/qwen3-8b-q8_0.gguf"]
    r = subprocess.run(COMPOSE + ["--profile", "tools", "run", "--rm", "--entrypoint", "python3", "llamacpp", "-c",
                                  TENSOR_TYPES, *args], text=True, capture_output=True, check=True)
    res = json.loads(r.stdout.strip().splitlines()[-1])
    (OUT / "tensors.json").write_text(json.dumps(res, indent=1))
    for q, kinds in res.items():
        print(q, {k: v for k, v in kinds.items() if k in ("attn_v.weight", "ffn_down.weight", "token_embd.weight", "output.weight")})
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ladder", action="store_true")
    ap.add_argument("--readback", action="store_true")
    ap.add_argument("--kld", action="store_true")
    ap.add_argument("--tensors", action="store_true")
    a = ap.parse_args()
    if a.ladder:
        ladder()
    if a.readback:
        readback()
    if a.kld:
        kld()
    if a.tensors:
        tensors()
