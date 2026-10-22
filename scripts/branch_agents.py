"""Find the agents on every branch of origin, run one on dev questions, and keep a log to compare them.

    python scripts/branch_agents.py list                                   # "<branch> agent" entries
    python scripts/branch_agents.py run --branch serin-91/chunking-cards-001-002 --config 008b-agent-950.yaml --limit 10
    python scripts/branch_agents.py log                                    # runs so far

An agent is a config on a branch whose `system` (after its `base:` chain) starts with "agent" and whose code
implements it (src/rag/agent.py is not the card-008 stub; agent_repair needs src/rag/agent_repair.py).

A run checks out that branch's commit in its own folder (out/agent_runs/worktrees/<commit>, detached, never
changes the branch or this checkout), links out/index to this checkout's indexes (index keys are content hashes,
so a shared folder is safe), then runs that branch's own scripts: build_index (skips existing indexes), run.py
(dev split only), grade.py, evaluate.py. Results are copied to out/agent_runs/results/<experiment> and a row is
added to out/agent_runs/log.jsonl. Each branch grades with its own judge config; the log records which.
Everything stays under out/ (not committed).
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "out" / "agent_runs"
WORKTREES, RESULTS, JOBS = HOME / "worktrees", HOME / "results", HOME / "jobs"
LOG = HOME / "log.jsonl"
CACHE = HOME / "branch_agents.json"
PYTHON = str(Path(sys.executable).with_name("python.exe"))  # also when this runs under pythonw.exe
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
STUB = 'raise NotImplementedError("card 008")'


def git(*args: str, cwd: Path = ROOT, check: bool = True) -> str:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8")
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


class Blobs:
    """Read many files from many commits through one `git cat-file --batch` process."""

    def __init__(self):
        self.p = subprocess.Popen(["git", "cat-file", "--batch"], cwd=ROOT, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE)

    def read(self, spec: str) -> str | None:
        self.p.stdin.write((spec + "\n").encode())
        self.p.stdin.flush()
        header = self.p.stdout.readline().decode().split()
        if len(header) < 3 or header[1] == "missing":
            return None
        data = self.p.stdout.read(int(header[2]))
        self.p.stdout.read(1)  # trailing newline
        return data.decode("utf-8", errors="replace")

    def close(self):
        self.p.stdin.close()
        self.p.wait()


def branches(fetch: bool = True) -> list[tuple[str, str]]:
    """(branch name without origin/, commit) for every remote branch."""
    if fetch:
        git("fetch", "origin", "--prune", "--quiet")
    out = git("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/remotes/origin")
    pairs = [line.split() for line in out.splitlines() if line.strip()]
    return [(ref.removeprefix("origin/"), sha) for ref, sha in pairs if ref not in ("origin", "origin/HEAD")]


def _resolve(blobs: Blobs, sha: str, name: str, seen=()) -> dict:
    text = blobs.read(f"{sha}:configs/{name}")
    if text is None:
        return {}
    d = yaml.safe_load(text) or {}
    base = d.pop("base", None)
    if base and base not in seen:
        merged = _resolve(blobs, sha, base, seen + (name,))
        for k, v in d.items():
            merged[k] = {**merged[k], **v} if isinstance(v, dict) and isinstance(merged.get(k), dict) else v
        return merged
    return d


def scan(fetch: bool = True) -> list[dict]:
    """Agent entries on every remote branch; cached per commit in out/agent_runs/branch_agents.json."""
    HOME.mkdir(parents=True, exist_ok=True)
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    found, blobs = [], None
    for branch, sha in branches(fetch):
        if sha not in cache or any("maker" not in e for e in cache[sha]["agents"]):
            blobs = blobs or Blobs()
            files = [f.split("/")[-1] for f in git("ls-tree", "--name-only", sha, "configs/").split()
                     if f.endswith(".yaml")]
            agent_py = blobs.read(f"{sha}:src/rag/agent.py") or ""
            has_repair = blobs.read(f"{sha}:src/rag/agent_repair.py") is not None
            code = git("rev-parse", f"{sha}:src/rag").strip()
            entries = []
            for f in files:
                cfg = _resolve(blobs, sha, f)
                system = str(cfg.get("system", ""))
                if not system.startswith("agent"):
                    continue
                if (system == "agent" and (not agent_py or STUB in agent_py)) or (system == "agent_repair" and not has_repair):
                    continue
                ident = hashlib.sha1(json.dumps([code, cfg], sort_keys=True, default=str).encode()).hexdigest()[:8]
                added = int(git("log", "-1", "--format=%ct", sha, "--", f"configs/{f}").strip() or 0)
                # when the config first appeared on this branch, and what the agent is (config + its implementation
                # file), so a copy of another teammate's agent can be told from the branch's own (latest_per_branch)
                first = git("log", "--diff-filter=A", "--format=%ct", sha, "--", f"configs/{f}").split()
                makers = git("log", "--diff-filter=A", "--format=%an", sha, "--", f"configs/{f}").splitlines()
                impl = "src/rag/agent_repair.py" if system == "agent_repair" else "src/rag/agent.py"
                origin = hashlib.sha1(json.dumps([git("rev-parse", f"{sha}:{impl}").strip(), cfg], sort_keys=True,
                                                 default=str).encode()).hexdigest()[:8]
                entries.append({"config": f, "name": cfg.get("name"), "system": system, "added": added,
                                "first_added": int(first[-1]) if first else added, "origin_key": origin,
                                "maker": makers[-1] if makers else "",  # who first committed this agent's config
                                "description": cfg.get("description", ""), "answer_model": cfg.get("answer", {}).get("model"),
                                "chunking": cfg.get("chunking", {}), "card": cfg.get("card"), "same_code_id": ident,
                                "judge": cfg.get("judge", {})})
            cache[sha] = {"date": git("log", "-1", "--format=%ad", "--date=format:%Y-%m-%d %H:%M", sha).strip(),
                          "author": git("log", "-1", "--format=%an", sha).strip(), "agents": entries}
        for e in cache[sha]["agents"]:
            found.append({**e, "branch": branch, "commit": sha[:7], "sha": sha, "date": cache[sha]["date"],
                          "author": cache[sha]["author"], "label": label(branch, e["config"], cache[sha]["agents"])})
    if blobs:
        blobs.close()
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return found


def label(branch: str, config: str, agents: list[dict]) -> str:
    """'<branch> agent', with the config name when the branch has more than one agent."""
    return f"{branch} agent" + (f" ({config.removesuffix('.yaml')})" if len(agents) > 1 else "")


def originals(agents: list[dict]) -> list[dict]:
    """Drop copies: the same agent (same config and implementation file) that first appeared on another branch
    earlier. A teammate who copies someone's agent files into their branch to compare does not make it theirs;
    agents shared through merged history (added in the same commit) count on every branch."""
    first = {}
    for a in agents:
        first[a["origin_key"]] = min(first.get(a["origin_key"], a["first_added"]), a["first_added"])
    return [a for a in agents if a["first_added"] <= first[a["origin_key"]]]


def latest_per_branch(agents: list[dict]) -> list[dict]:
    """One agent per branch: among the branch's own agents (copies dropped, see originals), the one whose
    config was committed last on that branch (ties: higher config number), labelled '<branch> agent'."""
    best: dict[str, dict] = {}
    for a in originals(agents):
        b = best.get(a["branch"])
        if b is None or (a["added"], a["config"]) > (b["added"], b["config"]):
            best[a["branch"]] = a
    return [{**a, "label": f"{a['branch']} agent",
             "added_at": datetime.fromtimestamp(a["added"]).strftime("%Y-%m-%d %H:%M")}
            for a in sorted(best.values(), key=lambda a: a["added"], reverse=True)]


def distinct_agents(agents: list[dict]) -> tuple[list[dict], list[dict]]:
    """Each distinct agent once. Branches that merged the same agent (same config and implementation file) carry
    a duplicate: keep the one on its maker's own branch (newest such branch), else the newest branch. Returns
    (shown, hidden); a hidden entry has 'same_as' = the label it duplicates."""
    latest, groups = latest_per_branch(agents), {}
    for a in latest:
        groups.setdefault(a["origin_key"], []).append(a)
    shown, hidden = [], []
    for group in groups.values():
        own = [a for a in group if a["author"] == a["maker"]]
        keep = max(own or group, key=lambda a: a["date"])
        shown.append(keep)
        hidden += [{**a, "same_as": keep["label"]} for a in group if a is not keep]
    return sorted(shown, key=lambda a: a["added"], reverse=True), hidden


# ---------------------------------------------------------------- run

MAX_PARALLEL = 3          # agent runs at once (each answers 4 questions at a time); the rest wait as "queued"
LOCKS = HOME / "locks"


class Lock:
    """An OS file lock (msvcrt): released by Windows when the holding process ends, even if it crashes."""

    def __init__(self, name: str):
        LOCKS.mkdir(parents=True, exist_ok=True)
        self.f = open(LOCKS / f"{name}.lock", "a+")

    def acquire(self, wait: bool = True) -> bool:
        import msvcrt
        while True:
            try:
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
                return True
            except OSError:
                if not wait:
                    return False
                time.sleep(2)

    def release(self):
        import msvcrt
        self.f.seek(0)
        msvcrt.locking(self.f.fileno(), msvcrt.LK_UNLCK, 1)

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, *exc):
        self.release()


def _slot() -> Lock:
    """Wait for one of MAX_PARALLEL run slots."""
    locks = [Lock(f"slot{i}") for i in range(MAX_PARALLEL)]
    while True:
        for lk in locks:
            if lk.acquire(wait=False):
                return lk
        time.sleep(3)


def _alive(pid: int | None) -> bool:
    if not pid:
        return False
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def _worktree(sha: str) -> Path:
    path = WORKTREES / sha[:10]
    with Lock("worktree"):  # two runs of the same commit must not both create its checkout
        if not (path / "scripts" / "run.py").exists():
            WORKTREES.mkdir(parents=True, exist_ok=True)
            if path.exists():  # a half-made checkout from an interrupted run
                git("worktree", "remove", "--force", str(path), check=False)
                shutil.rmtree(path, ignore_errors=True)
                git("worktree", "prune")
            git("worktree", "add", "--detach", str(path), sha)
        index = path / "out" / "index"
        if not index.exists():
            (path / "out").mkdir(exist_ok=True)
            (ROOT / "out" / "index").mkdir(parents=True, exist_ok=True)
            import _winapi  # a directory junction needs no admin rights on Windows
            _winapi.CreateJunction(str(ROOT / "out" / "index"), str(index))
    return path


def _env() -> dict:
    from dotenv import dotenv_values
    env = {**os.environ, **{k: v for k, v in dotenv_values(ROOT / ".env").items() if v}}
    env.update(LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false", PYTHONIOENCODING="utf-8")
    return env


def experiment_name(entry: dict, limit: int | None) -> str:
    slug = entry["branch"].replace("/", "-").replace(" ", "")
    return (f"dev_cmp_{slug}_{entry['config'].removesuffix('.yaml')}_{limit or 'all'}q_"
            f"{datetime.now():%m%d%H%M}")


def _job(exp: str, **update) -> dict:
    JOBS.mkdir(parents=True, exist_ok=True)
    path = JOBS / f"{exp}.json"
    job = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    job.update(update)
    path.write_text(json.dumps(job, ensure_ascii=False, indent=1), encoding="utf-8")
    return job


def run(entry: dict, limit: int | None, sets: str | None, exp: str) -> dict:
    """Build index (if missing), run, grade, evaluate on the branch's own code; returns the log row."""
    _job(exp, status="queued", step="queued", entry=entry, limit=limit, sets=sets, pid=os.getpid())
    slot = _slot()  # noqa: F841  held until this process ends (Windows releases the lock with the process)
    started = time.time()
    _job(exp, status="running", step="checkout", started=datetime.now().isoformat(timespec="seconds"))
    log_path = JOBS / f"{exp}.log"
    wt = _worktree(entry["sha"])
    _job(exp, worktree=str(wt))
    cfg = f"configs/{entry['config']}"
    steps = [("index", ["scripts/build_index.py", "--config", cfg]),
             ("run", ["scripts/run.py", "--config", cfg, "--split", "dev", "--name", exp]
              + (["--limit", str(limit)] if limit else []) + (["--sets", sets] if sets else [])),
             ("grade", ["scripts/grade.py", "--experiment", exp]),
             ("evaluate", ["scripts/evaluate.py", "--experiment", exp, "--with-runs"])]
    with log_path.open("a", encoding="utf-8") as log:
        for step, args in steps:
            _job(exp, step=step)
            log.write(f"\n=== {step}: {' '.join(args)}\n")
            log.flush()
            index_lock = Lock("index") if step == "index" else None  # the index folder is shared by every checkout
            if index_lock:
                index_lock.acquire()
            try:
                r = subprocess.run([PYTHON, "-X", "utf8", *args], cwd=wt, env=_env(), stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=NO_WINDOW)
            finally:
                if index_lock:
                    index_lock.release()
            if r.returncode:
                row = {"experiment": exp, "status": "failed", "failed_step": step, **_meta(entry, limit, sets, started)}
                _append(row)
                _job(exp, status="failed", step=step)
                return row
    dst = RESULTS / exp
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(wt / "results" / exp, dst)
    summary = json.loads((dst / "summary.json").read_text(encoding="utf-8"))
    row = {"experiment": exp, "status": "done", **_meta(entry, limit, sets, started), **_scores(summary)}
    _append(row)
    _job(exp, status="done", step="done")
    return row


def _meta(entry: dict, limit, sets, started: float) -> dict:
    return {"agent": entry["label"], "branch": entry["branch"], "commit": entry["commit"], "sha": entry["sha"],
            "config": entry["config"],
            "system": entry["system"], "answer_model": entry.get("answer_model"), "same_code_id": entry.get("same_code_id"),
            "limit": limit, "sets": sets, "started": datetime.fromtimestamp(started).isoformat(timespec="seconds"),
            "minutes": round((time.time() - started) / 60, 1)}


def _scores(s: dict) -> dict:
    sc, co, ca, la, rt = (s.get(k) or {} for k in ("scores", "cost", "calls", "latency_s", "retrieval"))
    return {"n": s.get("n_questions"), "errors": s.get("n_errors"), "correctness": sc.get("correctness_mean"),
            "fully_correct": sc.get("fully_correct"), "status_ok": sc.get("status_ok"),
            "citation_on_target": sc.get("citation_on_target"), "page_hit@5": rt.get("page_hit@5"),
            "evid@5": rt.get("evid@5"), "usd_per_question": co.get("usd_per_question"), "usd": co.get("usd"),
            "judge_usd": co.get("judge_usd"), "llm_per_question": ca.get("llm_per_question"),
            "searches_per_question": ca.get("searches_per_question"), "p50": la.get("p50"), "p90": la.get("p90"),
            "judge": f"{(s.get('config') or {}).get('judge', {}).get('model')} / {(s.get('config') or {}).get('judge', {}).get('prompt')}",
            "by_set": {k: v.get("correctness_mean") for k, v in (s.get("by_set") or {}).items()}}


def _append(row: dict):
    HOME.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_log() -> list[dict]:
    if not LOG.exists():
        return []
    return [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]


def jobs() -> list[dict]:
    if not JOBS.exists():
        return []
    out = []
    for p in sorted(JOBS.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if p.name.endswith(".entry.json"):
            continue
        job = json.loads(p.read_text(encoding="utf-8"))
        job["experiment"] = p.stem
        if job.get("status") in ("running", "queued"):
            # no live process behind it (older jobs kept no pid: no update for 15 minutes) -> it was stopped
            dead = not _alive(job["pid"]) if job.get("pid") else time.time() - p.stat().st_mtime > 900
            if dead:
                job = _job(p.stem, status="stopped")
                job["experiment"] = p.stem
        if job.get("status") == "running" and job.get("worktree"):
            job["done_questions"] = _done(Path(job["worktree"]), p.stem)
        out.append(job)
    return out


def _done(wt: Path, exp: str) -> int:
    db = wt / "out" / "runs.db"
    if not db.exists():
        return 0
    import sqlite3
    with sqlite3.connect(db) as con:
        try:
            return con.execute("SELECT COUNT(DISTINCT qid) FROM runs WHERE experiment = ? AND status != 'error'",
                               (exp,)).fetchone()[0]
        except sqlite3.Error:
            return 0


def sha_of(row: dict) -> str:
    """Full commit of a log row (older rows kept only the short hash)."""
    return row.get("sha") or git("rev-parse", row["commit"]).strip()


_CODE = """
import json, sys
sys.path[:0] = ["src", "."]
from rag.env import setup
setup()
from rag.config import load_config
from rag.systems import build_system
agent = build_system(load_config("configs/{config}"))
{body}
"""


def in_checkout(sha: str, config: str, body: str, timeout: int = 300) -> dict:
    """Run `body` with `agent` built from that commit's own code and config; body prints one JSON object."""
    wt = _worktree(sha)
    r = subprocess.run([PYTHON, "-X", "utf8", "-c", _CODE.format(config=config, body=body)], cwd=wt, env=_env(),
                       capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    lines = [line for line in r.stdout.splitlines() if line.startswith("{")]
    if r.returncode or not lines:
        raise RuntimeError((r.stderr or r.stdout).strip()[-800:])
    return json.loads(lines[-1])


def graph_of(sha: str, config: str) -> str:
    """draw_mermaid() of the agent graph on that commit (no API calls)."""
    return in_checkout(sha, config, 'print(json.dumps({"mermaid": agent.graph.get_graph().draw_mermaid()}))',
                       timeout=120)["mermaid"]


CHUNKS = HOME / "chunks"


def chunks_of(sha: str, config: str, scope: str = "B") -> list[dict]:
    """The chunks that commit's own chunking code makes with that config (no API calls), cached per commit:
    [{chunk_id, source, page, pages, chars, content}]. The same pages as its index build (indexable, in scope)."""
    path = CHUNKS / f"{sha[:10]}_{config.removesuffix('.yaml')}_{scope}.json"
    if not path.exists():
        CHUNKS.mkdir(parents=True, exist_ok=True)
        body = (
            "from rag import ROOT\nfrom rag.chunking import chunk_pages\nfrom rag.ingest import in_scope, indexable, load_pages\n"
            "cfg = agent.cfg\n"
            f"pages = [p for p in load_pages(ROOT / cfg['corpus']['pages']) if indexable(p, cfg) and in_scope(p, cfg, {scope!r})]\n"
            "out = [{'chunk_id': c['chunk_id'], 'source': c['source'], 'page': c['page'], 'pages': c.get('pages') or [c['page']],\n"
            "        'chars': len(c['content']), 'content': c['content']} for c in chunk_pages(pages, cfg)]\n"
            f"open({str(path)!r}, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False))\n"
            "print(json.dumps({'n': len(out)}))")
        in_checkout(sha, config, body, timeout=300)
    return json.loads(path.read_text(encoding="utf-8"))


def live_run(sha: str, config: str, question: str, scope: str) -> dict:
    """One question through that commit's agent (API calls); returns the system result dict."""
    body = (f"import time\nstart = time.perf_counter()\nres = agent.run({question!r}, {scope!r})\n"
            "res['latency_s'] = round(time.perf_counter() - start, 1)\n"
            "print(json.dumps(res, ensure_ascii=False, default=str))")
    return in_checkout(sha, config, body)


def start(entry: dict, limit: int | None, sets: str | None) -> str:
    """Start `run` in a background process that outlives the caller (the Streamlit page)."""
    exp = experiment_name(entry, limit)
    JOBS.mkdir(parents=True, exist_ok=True)
    (JOBS / f"{exp}.entry.json").write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
    args = [str(Path(PYTHON).with_name("pythonw.exe")), "-X", "utf8", str(Path(__file__)), "run-entry", exp] \
        + (["--limit", str(limit)] if limit else []) + (["--sets", sets] if sets else [])
    _job(exp, status="queued", step="queued", entry=entry, limit=limit, sets=sets)
    _job(exp, pid=_spawn(args))
    return exp


def _spawn(args: list[str]) -> int:
    """Start a windowless process that is not a child of this one. The Streamlit server (and the Claude/IDE
    shell) run inside a Windows job object that kills its processes when it closes and may forbid breaking
    away, so the process is created by WMI (Win32_Process.Create), like one started from the Start menu."""
    cmd = subprocess.list2cmdline(args).replace("'", "''")
    ps = (f"$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments "
          f"@{{CommandLine='{cmd}'; CurrentDirectory='{ROOT}'}}; if ($r.ReturnValue -ne 0) {{ exit 1 }}; $r.ProcessId")
    r = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], capture_output=True, text=True,
                       creationflags=NO_WINDOW)
    if r.returncode == 0 and r.stdout.strip().isdigit():
        return int(r.stdout.strip())
    p = subprocess.Popen(args, cwd=ROOT, creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    return p.pid


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    r = sub.add_parser("run")
    r.add_argument("--branch", required=True)
    r.add_argument("--config", required=True)
    r.add_argument("--limit", type=int)
    r.add_argument("--sets")
    e = sub.add_parser("run-entry")  # used by start(): the entry is already saved under jobs/
    e.add_argument("experiment")
    e.add_argument("--limit", type=int)
    e.add_argument("--sets")
    sub.add_parser("log")
    args = p.parse_args()
    if sys.stdout:  # None under pythonw.exe (background runs)
        sys.stdout.reconfigure(encoding="utf-8")
    if args.cmd == "list":
        for a in scan():
            print(f"{a['label']:70} {a['commit']} {a['system']:13} {a['answer_model']} same-code:{a['same_code_id']}")
    elif args.cmd == "run":
        entry = next((a for a in scan() if a["branch"] == args.branch and a["config"] == args.config), None)
        if not entry:
            sys.exit(f"no agent {args.config} on {args.branch}; see: python scripts/branch_agents.py list")
        print(json.dumps(run(entry, args.limit, args.sets, experiment_name(entry, args.limit)), ensure_ascii=False, indent=1))
    elif args.cmd == "run-entry":
        entry = json.loads((JOBS / f"{args.experiment}.entry.json").read_text(encoding="utf-8"))
        try:
            run(entry, args.limit, args.sets, args.experiment)
        except Exception as ex:  # keep the failure visible on the page
            _job(args.experiment, status="failed", error=f"{type(ex).__name__}: {ex}")
            raise
    else:
        for row in read_log():
            print(row["started"], row["status"], row["agent"], row.get("n"), row.get("correctness"))


if __name__ == "__main__":
    main()
