# <Project title>

<One sentence: what it does for whom.>

Status: reference implementation with synthetic data. Version: `pNN-vX.Y.Z`.

<Demo GIF or link to 2 to 4 minute video>

## The problem

<Three to five sentences from the client's point of view. Concrete, no hype.>

## What it does

<Short paragraph. What happens to one item from arrival to finish.>

## Architecture

<Mermaid diagram>

<Two or three sentences explaining the main path.>

## Why n8n, and where n8n is not used

<What n8n does here (orchestration, integrations, human steps). What the backend does and why (tests, state, security, performance). Link the ADR.>

## Workflows

| Workflow | Trigger | Responsibility |
|---|---|---|

<Canvas screenshot of the main workflow.>

## Run it in 5 minutes

```bash
git clone https://github.com/Aliipou/n8n-production-systems
cd n8n-production-systems
cp .env.example .env
make up P=<project>
make demo P=<project>
```

<URLs printed by make up. One-time n8n owner setup note.>

## Failure modes

| Scenario | What happens | Evidence |
|---|---|---|

<Every row links to a test or a chaos report. Include at least one "what happens when this fails" walkthrough with screenshots.>

## Observability

<Logs, metrics, dashboards, alerts that cover this project.>

## Security

<Authentication of every entry point, secret handling, data retention, what is not protected.>

## Deployment

<How this would run outside a laptop: minimum resources, queue mode, backups, upgrades. What was actually tested.>

## Results

<Only numbers produced by scripts in this repo. For each: value, date, hardware, model, dataset, script path. "Not measured yet" if missing.>

## Cost

<Measured LLM tokens and cost per item with price source and date. Infrastructure estimate with assumptions.>

## Limitations

<Honest and specific. What it does not handle, what would break first at higher volume, what needs work before real use.>

## Decisions

<Links to ADRs.>

## License

MIT for code in this repository. n8n is not included and is licensed separately by n8n GmbH.
