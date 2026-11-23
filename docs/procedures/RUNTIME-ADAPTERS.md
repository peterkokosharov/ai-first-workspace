# Runtime adapters for Roni

Status: design note. Roni today has one file, `roni_claude`, holding hooks and
other Claude-specific wiring. The goal is to run the same workspace on rex,
codex, goose, opencode and Claude, then let each user pick a favourite. rex is
the reference runtime: if the contract passes on rex, it is ready to be ported.

## Rule 1: the factory returns capabilities, not a copy of `roni_claude`

Claude hooks have no equivalent in rex, goose, codex or opencode. Do not copy
`roni_claude` into `roni_codex`, `roni_rex`, etc. Define one interface and keep
every runtime's quirks inside its own adapter:

```python
class RuntimeAdapter(Protocol):
    name: str
    capabilities: frozenset[str]   # hooks, permission, resume, thinking,
                                   # tool_events, cancel

    def launch(self, cwd: Path, key_names: dict[str, str]) -> Process: ...
    def read_rules(self, cwd: Path) -> list[str]: ...
    def events(self, proc: Process) -> Iterator[Event]: ...
    def confirm_push(self) -> bool: ...
```

Claude-specific code — the hooks file, `@import` in `CLAUDE.md`, thinking
display — stays in `adapters/claude.py`. Core never imports it directly. When a
runtime has no `hooks`, degrade to an explicit CLI confirmation instead.

## Rule 2: one factory, explicit choice

```python
ADAPTERS = {
    "claude": ClaudeAdapter,
    "rex": RexAdapter,
    "codex": CodexAdapter,
    "goose": GooseAdapter,
    "opencode": OpenCodeAdapter,
}

def make_runtime(name: str | None = None) -> RuntimeAdapter:
    name = name or os.environ.get("RONI_RUNTIME") or detect_single()
    return ADAPTERS[name]()
```

`detect_single()` returns a result only when exactly one runtime is found.
Otherwise require `RONI_RUNTIME`. Never silently take the first CLI on `PATH`.

## Rule 3: add a runtime as one file plus one matrix row

Suggested order:

1. **rex first** (the reference). `rex --jsonl` is one persistent process;
   events are `token`, `tool_start`, `tool_end`, `ready`, `error`; cwd is
   passed to the child. This is the smallest, cleanest adapter.
2. **Claude second** — move the contents of `roni_claude` into
   `adapters/claude.py` without duplicating it elsewhere.
3. codex, goose, opencode — each becomes one adapter module and one row in the
   smoke matrix. Core stays unchanged.

See the rex-side contract and its open items in
`docs/REX-HANDOFF.md` in the rex repository.

## Rule 4: invariants every adapter must keep

- An adapter resolves `service:key` **names only**. It never reads a secret
  value into the agent's context; values stay in the OS keyring / kiko gateway
  and clients use a dummy key.
- One runtime process per session. Roles are capability profiles inside that
  process, not one extra CLI process per role.
- `confirm_push()` is mandatory for every adapter. For Claude it is wired to
  hooks; for the others it is an explicit confirmation. "No push without a
  separate yes" is an invariant, not a Claude feature.
- Use relative paths in tools; the guard rejects absolute paths.

## Rule 5: prove the matrix, do not assume it

One parameterized contract test runs against every adapter with a fake runtime
process: rules read, key names visible, events mapped, push denied without
confirmation. The real smoke matrix is OS x runtime; each cell asks the same
three questions — reply language, rules read, key names seen (never values).

Only after rex passes both does "works on rex, therefore works everywhere"
become a checked statement instead of a hope.
