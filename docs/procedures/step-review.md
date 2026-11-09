# Review after each finished step

Goal: a different, stronger model checks every finished step before it is committed.
If no other model is available, the review is optional: the same model reviews in a
fresh reviewer role (read only, goal and diff only) and says so in the result.
On Windows type `py` instead of `python3`.

## When
- You finished one step (code, tests or docs) and the tests pass.

## Steps
1. Write the step goal in one or two sentences.
2. Run `git status` and `git diff`. Check that only files of this step changed.
3. Pick a reviewer model that is NOT the model you are. Prefer a stronger one.
   If you do not know which model you are, ask the user.
   - List models: type `/models` in opencode, or run `opencode models` in a terminal.
   - Check the inventory too: `python3 tools/inventory.py list models`.
4. Start the reviewer with only the goal and the diff (keep its context small).
   The reviewer is a fresh reviewer role in this session (it only reads), or an
   opencode subagent. Pick a reviewer model that is not you if one is available.
   - Starting another opencode process (`opencode run --agent plan -m <provider/model>`,
     or `python3 tools/run_opencode.py run ...` for models with a stored key) only when
     the user names it.
   - No second model? Review in a fresh reviewer role yourself and write
     `Review: PASS (<your model>, same model, fresh role)`.
   - Or ask the user to run the review.
   - UNVERIFIED: the opencode subagent mechanism and `--agent plan` (check with
     `opencode run --help`). Never start claude, gemini, goose, codex or another opencode
     for this unless the user names it.
5. Use this prompt (fill in the goal):
   ```text
   Review the uncommitted change in this folder. Goal: <goal>.
   Run `git diff` to see it. Read other files only if you must.
   Do not edit, create or delete any file. Do not commit.
   List each finding as file:line - problem - fix.
   End with one line: PASS or FAIL.
   ```
6. Read the answer.
   - PASS: go on with docs/procedures/commit.md.
   - FAIL: fix the findings, run the tests, then go back to step 2.
7. Stop after 2 FAIL rounds. Show the findings to the user and ask what to do.
8. Write the result in the commit message, e.g. `Review: PASS (<model>)`.

## Rules
- The reviewer only reads. It never edits files and never commits.
- Never send a key, token or `.env` content to the reviewer.
- Save a long review in `out/review-<date>.md` if the user wants it (out/ is not in git).
