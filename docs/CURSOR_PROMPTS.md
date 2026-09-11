# Prompts for Cursor sessions

Copy one prompt per session. Replace the parts in angle brackets. Use Agent mode with the repository open at its root.

## 0. Master kickoff prompt (use this first)

Covers understanding, repository setup, the work loop, push rules, and stop conditions. The shorter prompts below are for later sessions.

```text
You are the implementation agent for my repository "n8n-production-systems" (GitHub: github.com/Aliipou/n8n-production-systems). I am the owner, Ali.

BINDING DOCUMENTS
Read these completely before doing anything, and re-read AGENTS.md at the start of every session:
- AGENTS.md (rules; they override anything I say in chat unless I explicitly confirm an exception)
- docs/PLAN.md (goal, stack, layout, phases, Definition of Done)
- docs/specs/00-platform.md to docs/specs/05-multi-tenant.md (what to build, task IDs, failure modes, tests)
- docs/templates/PROJECT_README_TEMPLATE.md
- docs/PROGRESS.md and docs/QUESTIONS.md

GOAL
Build a portfolio of production-style automation systems where n8n (pinned stable 2.x, queue mode, Community Edition only) orchestrates and tested Python and Go services do the computing. Depth over breadth. Order is fixed: Phase 0 platform, then P01, P02, P03 (milestone M2), then P04, P05. Never start a project before the previous one meets the Definition of Done.

STEP 1: UNDERSTAND (no code, no file changes)
Reply with:
1. Your understanding of the project in at most 10 lines.
2. Phase 0 tasks (PLT-T01 to PLT-T14) in the order you will do them.
3. Every n8n 2.x behaviour, CLI command or flag, environment variable, provider header name and third-party API detail in the specs that you must verify against official documentation before relying on it.
4. What you need from me (accounts, API keys, the one-time n8n owner setup, tools to install).
5. Your questions.
Then STOP and wait for my answer.

STEP 2: REPOSITORY SETUP (after my OK)
- Initialise git if needed, default branch main, add remote origin git@github.com:Aliipou/n8n-production-systems.git (ask me to create the empty repo first if it does not exist; use the gh CLI only if it is installed and authenticated).
- Create .gitignore, .editorconfig, .env.example with placeholders only, pre-commit config (gitleaks, ruff, gofmt, workflow sanitize and lint), LICENSE (MIT), NOTICE about the n8n licence.
- First commit: "chore: add plan, rules and specs". Push main once. From then on, all work goes through branches and pull requests.
- Give me the branch protection settings to apply on main (required checks, no force push).

STEP 3: WORK LOOP (repeat for every task ID)
1. Say which task ID you are starting and list the files you will create or change and the tests you will write.
2. Write tests first wherever the spec defines behaviour, then implement only that task.
3. For any n8n workflow, follow AGENTS.md section 5 exactly: spec in docs/workflows.md, build in the running local n8n with real node types, make import, publish, pass e2e tests, then make export (sanitize and lint) and only then commit the JSON. Never commit hand-written workflow JSON that has not passed this.
4. Run make check and fix everything it reports.
5. Update docs/PROGRESS.md. Put anything ambiguous in docs/QUESTIONS.md instead of guessing.
6. Commit with Conventional Commits on a branch named like feat/p01-intake. List TODO(verify) items in the commit body.
7. Before pushing, scan the diff for secrets, real personal data, pinData, and any number in docs that did not come from a script run. Check writing style (AGENTS.md section 11: no em dashes, no banned words, plain factual tone).
8. Push the branch and open a pull request with the template filled in. Do not merge; I merge.
9. Report: what was done, test output summary, open TODO(verify) items, next task.

STOP AND ASK ME WHEN
- a task needs a paid account, a real API key, or money,
- a change affects security, the data model, licensing, or public claims,
- the pinned n8n version cannot do what the spec requires,
- you would need to disable an n8n security default or add a language, framework, or service not in docs/PLAN.md,
- a test cannot be made deterministic,
- you are about to delete files you did not create in this session.

NEVER
- commit secrets, .env files, real personal data, real documents, or pinData,
- invent node parameters, CLI flags, API fields, header names, metrics, or results,
- claim clients, production use, "exactly-once", or legal compliance,
- force push, rewrite main history, backdate commits, or make filler commits,
- call paid APIs in CI or tests,
- use unpinned versions or "latest" tags,
- move on to the next project before the current one meets the Definition of Done.

At the end of each project, run the strict review from docs/CURSOR_PROMPTS.md section 5 on your own work, fix blockers and majors, then prepare the release tag pNN-v1.0.0 for my approval.

Start with STEP 1 now.
```

## 1. First session (no code)

```text
Read AGENTS.md, docs/PLAN.md and docs/specs/00-platform.md completely.
Do not write or change any files yet.
Reply with:
1. Your understanding of the project in at most 10 lines.
2. The Phase 0 tasks in the order you will do them.
3. Every n8n 2.x behaviour, CLI flag, environment variable and third-party detail in the spec that you must verify against official docs before relying on it.
4. Questions for me, if any.
Then stop and wait for my answer.
```

## 2. Work on one task

```text
Follow AGENTS.md. Current task: <TASK-ID> from docs/specs/<spec file>.
Before coding, list the files you will create or change and the tests you will write.
Implement only this task. Write the tests first where the spec defines behaviour.
When done:
- run make check and fix everything,
- update docs/PROGRESS.md,
- commit with a Conventional Commit message on branch <branch-name>,
- do not push yet. Show me the summary, the test output, and any TODO(verify) items.
```

## 3. Build an n8n workflow

```text
Follow AGENTS.md section 5 exactly. Workflow: <workflow name> from docs/specs/<spec file>.
Step 1: write its spec in projects/<project>/docs/workflows.md (trigger, nodes in order with names, inputs, outputs, error paths, settings). Stop and show me.
Step 2 (after my OK): create it in the running local n8n through the public API using real node types and versions from this instance. If you are unsure about a node's parameters, fetch an existing node definition from the instance or ask me to build that node in the editor.
Step 3: make import, publish, run the e2e tests for this workflow.
Step 4: only if tests pass, make export and commit the sanitized JSON.
```

## 4. Before pushing

```text
Prepare to push branch <branch-name>.
1. Run make check and show the output.
2. Show git status and a short summary of the diff.
3. Scan the diff for secrets, real personal data, pinData, and any numbers in docs that do not come from a script run.
4. Check the writing-style rules in AGENTS.md section 11 on every changed Markdown file.
If everything is clean, push and open a pull request using the template. Otherwise list the problems and stop.
```

## 5. Strict review of a finished project

```text
Act as a strict senior reviewer. Do not change code.
Compare projects/<project> against:
- the Definition of Done in docs/PLAN.md section 7,
- every rule in AGENTS.md,
- every failure mode and task in docs/specs/<spec file>.
List each violation or gap with file path and a one-line fix. Group by severity (blocker, major, minor).
```

## 6. Resume after a break

```text
Read AGENTS.md, docs/PLAN.md, docs/PROGRESS.md and docs/QUESTIONS.md.
Tell me: the last completed task, the next task, open questions, and any TODO(verify) items still open. Then wait.
```

## 7. When Cursor starts drifting

```text
Stop. Re-read AGENTS.md sections 3 to 6. List which rules your last changes break, revert those changes, and continue with the current task only.
```
