# Work split over several agents

Goal: one lead agent (orc) splits work into small steps and gives each role one job.
On Windows type `py` instead of `python3`.

## Roles
- **orc**: plans, splits the work into small steps, writes each brief, checks results.
- **coder**: changes code for one step. Nothing else.
- **test-coder**: writes tests from the step goal, not from the code.
- **qa**: runs the tests and reports pass or fail with the output.
- **reviewer**: follows docs/procedures/step-review.md. Reads only.
- **git-pusher**: prepares the push line and prints it. A human pushes.

## Brief for each role (keep it short)
1. Goal of the step in one or two sentences.
2. The files it may change (for qa and reviewer: none).
3. The command that shows it is done (usually the test command).
4. "Read AGENTS.md first. Do not push."

## Steps for orc
1. Split the user's task into small steps. One step = one goal = one commit.
2. Show the list to the user. Start only after an order.
3. For each step, in this order:
   1. test-coder writes the tests for the goal.
   2. coder changes the code.
   3. qa runs `python3 -m unittest discover -s tools/tests -t . -v`
      (or the project's own test command) and reports pass or fail + output.
   4. reviewer reviews the diff (docs/procedures/step-review.md).
4. All OK: commit the step (docs/procedures/commit.md).
5. Not OK and you cannot fix it:
   - Not committed yet: ask "Shall I undo the changes in <files>?".
     After a reply that starts with "да" or "yes": `git restore <files>`.
   - Already committed: ask "Shall I revert commit <hash>?".
     After "да" or "yes": `git revert <hash>`.
6. When all steps are committed, git-pusher follows docs/procedures/github-deploy.md
   (agent steps only): it prints `git push origin <branch>` and asks the human to run it.

## No subagents
Most free setups have no subagents. Then one agent plays the roles in turn:
1. Before each role, read this file and AGENTS.md again.
2. Say which role you play now, e.g. "Role: qa".
3. Do only that role's job, then switch to the next role.
