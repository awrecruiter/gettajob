# gettajob v1

Automated job hunting pipeline — foundation connectors.

See `PRD.md` for the full product spec. V1 covers the four connector foundation: Greenhouse, Lever, Ashby, USAJobs. Scoring, resume generation, and the tracking dashboard arrive in later versions.

## Install

```
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Configure

Copy `.env.example` to `.env` and fill in USAJobs credentials (request one at https://developer.usajobs.gov/apirequest/). The USAJobs `User-Agent` is the email address you registered with.

Edit `config.json` to add companies. Find each slug from the company's careers page URL:

- Greenhouse: `boards.greenhouse.io/<slug>`
- Lever: `jobs.lever.co/<slug>`
- Ashby: `jobs.ashbyhq.com/<slug>`

## Run

```
gettajob init                     # create the SQLite DB (gettajob.db)
gettajob run                      # fetch all configured sources
gettajob run --source greenhouse  # fetch a single source
gettajob list --limit 20          # show most recent jobs
gettajob list --company Anduril
```

Every run upserts by `(source, external_id)`. New jobs are inserted; repeat sightings update `last_seen`. Connector-run history is stored in `connector_runs`.
