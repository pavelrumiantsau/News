# Source analysis

Why these sources, why not the others, and what the honest limits are.

## The problem with "top news per country"

No free service publishes an editorially curated "top 3 stories" for all ~195
countries. What exists is:

| Option | Coverage | Trust | Verdict |
|---|---|---|---|
| Wire services (Reuters/AP) direct RSS | Global but selective | Very high | Reuters killed public RSS; AP blocks scraping (403) |
| A hand-picked national outlet per country | Complete only if you maintain ~195 feeds | Mixed | Feeds break constantly; many countries have no free, credible outlet |
| GDELT Project API | Every country | **Low** — indexes an unvetted long tail | Rejected, see below |
| News aggregator APIs (NewsAPI, GNews, etc.) | Good | Good | All have paid tiers / key limits; conflicts with "no ongoing cost" |
| Google News RSS + a trust allowlist | Every country | **Inherited from the allowlist** | **Chosen** |

### Why GDELT was rejected

GDELT is the obvious technical answer — free, global, country-tagged. But it
indexes essentially everything that looks like news, including content farms and
state propaganda, with no reliability weighting. It also rate-limits to one
request per five seconds and refused sustained querying during testing. For a
brief whose first rule is "verified stable sources", an unvetted index is the
wrong foundation.

### Why Google News RSS works here

Two properties matter, both verified during build:

1. **It honours `site:` and `OR` operators.** A query can be constrained to a
   fixed list of trusted domains *before* results are returned. Trust is enforced
   at the query, not merely filtered afterwards.
2. **Its `<source url="…">` element gives the publisher's real domain**, so every
   item can be checked against the allowlist and the denylists independently.

It is free, needs no key, and has no per-day cost. The feed is licensed for
personal, non-commercial reading — which is exactly this use.

The catch: an unconstrained query returns junk. Searching "Nauru" without the
allowlist returned Encyclopedia Britannica, AccuWeather, World Population Review
and travel blogs. Everything below exists to fix that.

## The trust model

An item is shown only if it passes **all four** gates.

**1. Publisher is on the allowlist** (`config/sources.json`).

- **Tier 1** — international wires and public-service broadcasters: Reuters, AP,
  BBC, Al Jazeera, DW, France 24, RFI, Euronews, NPR, PBS, CBC, ABC Australia,
  SBS, RNZ, SWI swissinfo, The Guardian, RFE/RL, VOA, UN News, ReliefWeb, ANSA,
  EFE, Kyodo, CNA Singapore, Africanews, Yle, NRK, DR, SVT, RTÉ.
- **Tier 2** — established national and regional outlets, roughly 170 of them,
  chosen for editorial track record and free access: Premium Times (Nigeria),
  Daily Maverick (South Africa), The Hindu and The Wire (India), Dawn (Pakistan),
  Rappler (Philippines), Balkan Insight, Eurasianet, OC Media, Islands Business,
  Stabroek News (Guyana), Kuensel (Bhutan), Vanuatu Daily Post, and so on.

Tier drives ranking: a Reuters story outranks a national-paper story of equal
freshness, so you read the best-sourced version of an event first.

**2. Publisher is not on a denylist.** Three separate lists:

- **Paywalled** (~50 domains) — NYT, WSJ, FT, Bloomberg, The Economist, Le Monde,
  Telegraph, Haaretz, Nikkei and similar. Excluded per your rule; a headline you
  cannot open is not useful.
- **State propaganda / unreliable** (~80 domains) — RT, Sputnik, TASS, RIA, Global
  Times, Xinhua, CGTN, Press TV, KCNA, teleSUR, BELTA, plus Western low-credibility
  outlets (Zero Hedge, Gateway Pundit, Infowars, Epoch Times, Global Research,
  Strategic Culture, The Grayzone). This list is about *editorial independence*,
  not about which country a publisher sits in.
- **Not news** (~130 domains) — reference sites, weather, press-release wires,
  stock-tip sites, travel blogs, aggregators, sports and celebrity outlets. This
  is what actually contaminated small-country results in testing.

**3. Headline is not topic noise.** Regex rules drop match reports, transfer
rumours, horoscopes, share-price moves, "how to watch" pages and publisher
boilerplate. Sport is *demoted* rather than dropped — for the smallest states it
is sometimes the only coverage that exists, so it surfaces only when nothing
else does.

**4. The story is actually about that country.** The country, its capital, its
demonym or a named region must appear in the headline (strong) or the summary
(weaker, ranked lower), with word boundaries so "Chad" does not match "Chadwick"
and "Nevis" does not match "Ben Nevis". This was the single biggest quality win:
without it, Suriname's page filled with Leeds United transfer gossip.

### Judgement calls worth knowing about

- **RFE/RL and VOA** are US-government-funded. They are included because both
  operate under a statutory editorial firewall and are, in practice, the best
  free reporting available on Central Asia, the Caucasus and Belarus. Treat them
  as good reporting from an interested party.
- **Al Jazeera** is Qatari state-funded; its English newsroom is editorially
  strong and indispensable for the Middle East and Africa. Included.
- **Anadolu (aa.com.tr)** is a Turkish state wire with real reporting and a
  pro-government slant. Included at tier 2; TRT World and Daily Sabah are not.
- **Russian and Belarusian coverage** comes from independent outlets in exile —
  Meduza, Novaya Gazeta Europe, The Bell, The Moscow Times, Zerkalo, Nasha Niva —
  not from domestic state media.
- **China, Iran, North Korea, Eritrea, Turkmenistan** have no free domestic press.
  Their coverage is necessarily external (Reuters, BBC, RFE/RL, SCMP). That is a
  real limitation, not a bug to be fixed.

## Language handling

Priority is English → Ukrainian → Russian → native, as you asked.

- Every country is queried in English first.
- 74 countries additionally get a query against their national Google News
  edition in the local language; Ukraine (uk), Russia, Belarus and Kazakhstan
  (ru) are among them.
- Non-English items carry a language tag in the interface and a ranking penalty,
  so they appear only when English coverage is thin — which is the intent.
- A stopword heuristic catches regional-language output from English-domain
  publishers (BBC Somali, BBC Hausa) and demotes it the same way.

## What this cannot do

Stated plainly, because these are the things that will annoy you later:

- **It reports what is covered, not what is happening.** A quiet week in Kiribati
  and an unreported crisis in Kiribati look identical here. Countries with a
  suppressed or absent press are systematically under-represented.
- **Ranking is keyword-driven, not comprehension-driven.** No model reads these
  headlines. Significance scoring uses word lists, so it will occasionally rank a
  minor story above a major one.
- **Google News is a single point of failure.** If Google changes or withdraws the
  RSS endpoint, the collector stops working. The per-country and regional feeds
  in `sources.json` are the mitigation, but it would need code changes.
- **Small-state coverage is thin by nature.** For Tuvalu or Palau you will often
  see a story from several weeks ago. The interface labels this rather than
  hiding it.
- **The allowlist encodes my judgement.** You should edit it. It is plain JSON
  with a one-line justification beside every domain.
