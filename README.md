# World Desk

A daily news brief covering **every country on earth**, built from trusted,
free-to-read sources. No API keys, no subscriptions, no AI running on a schedule.

Open one page in the morning: a dozen global headlines, then all 197 countries
A–Z, each showing up to three stories. Click a country to see the rest. Countries
with nothing to report say so.

```
┌──────────────────────────────────────────────────────────────┐
│ World Desk        24 August 2026 · 197 countries · 1,412 …   │
│                   [ filter… ]  All Europe Asia Africa …      │
├──────────────────────────────────────────────────────────────┤
│ ACROSS THE WORLD TODAY                                       │
│  UKRAINE  Zelensky asked what he knew about corruption…      │
│  DR CONGO Attacks on medics make Ebola fight harder…         │
├──────────────────────────────────────────────────────────────┤
│ EUROPE · 45                                                  │
│ ▶ Albania      Rama unveils cabinet reshuffle…    3 stories  │
│ ▶ Andorra      …                          carried forward    │
│ ▼ Ukraine                                        12 stories  │
│     Ukrainian drone attack kills three in Krasnodar          │
│     Reuters · 4h ago · wire / public                         │
└──────────────────────────────────────────────────────────────┘
```

## How it works

A single Python script (stdlib only) queries Google News RSS once or twice per
country, constrained by `site:` operators to a curated allowlist of trusted
publishers, then filters and ranks the results deterministically. It writes
`docs/news.json`. The page is static HTML that reads that file.

**No AI is involved in the daily run.** Relevance, trust and ranking are regex and
table lookups. Cost per day: zero.

Read [SOURCES.md](SOURCES.md) for which sources were chosen, which were rejected
(and why), and the honest limitations.

## Setup — GitHub Pages

1. Create a repository and push this directory:

   ```bash
   cd ~/Documents/News
   git init && git add . && git commit -m "World Desk"
   gh repo create world-desk --private --source=. --push
   ```

   (Public works too; Pages on a private repo needs a paid plan.)

2. In the repo: **Settings → Pages → Source → GitHub Actions**.

3. In **Settings → Actions → General → Workflow permissions**, select
   *Read and write permissions*.

4. **Actions → Rebuild world news → Run workflow** to build immediately.
   After that it runs itself at 05:10 UTC daily.

Your page: `https://<username>.github.io/world-desk/`
Bookmark it on your phone and laptop.

## Running it locally

```bash
python3 collect.py                    # full run, ~5 minutes
python3 collect.py --only UA,PL,DE    # just a few countries
python3 collect.py --limit 20         # first 20, for quick iteration

python3 -m http.server -d docs 8000   # then open http://localhost:8000
```

Opening `docs/index.html` directly via `file://` will not work — the page
fetches `news.json`, which browsers block on the file protocol. Use the
`http.server` line above.

## Tuning it

| I want to… | Edit |
|---|---|
| Trust a new publisher | `config/sources.json` → `tier1` or `tier2` (+ `bloc_domains` to prioritise it regionally) |
| Ban a publisher | `config/sources.json` → `deny_paywall` / `deny_state_propaganda` / `deny_not_news` |
| Stop seeing a kind of story | `config/sources.json` → `topic_noise_patterns` (regex) |
| Change what counts as important | `config/sources.json` → `significance_boost_patterns` |
| Add search terms for a country | `tools/build_countries.py` → `TABLE`, then re-run it |
| Show more/fewer headlines | `collect.py` → `TOP_N` / `KEEP_N`; `docs/app.js` → `TOP_N` |
| Change the schedule | `.github/workflows/daily.yml` → `cron` |

After editing `tools/build_countries.py`:

```bash
python3 tools/build_countries.py     # regenerates config/countries.json
```

## Layout

```
collect.py                    the collector — one file, stdlib only
config/sources.json           trust tiers, denylists, noise patterns
config/countries.json         197 countries (generated)
tools/build_countries.py      editable country table → countries.json
docs/index.html               the dashboard
docs/style.css                styling, light + dark
docs/app.js                   rendering, filtering, expand/collapse
docs/news.json                generated daily; committed so history survives
.github/workflows/daily.yml   the cron job
SOURCES.md                    source analysis and limitations
```

## Country list

197 entries: the 193 UN member states, the two observer states (Vatican City,
Palestine), plus Kosovo and Taiwan. Dependencies and territories are not listed
separately; Greenland, Hong Kong, Western Sahara and similar are folded into
their administering state's search terms.
