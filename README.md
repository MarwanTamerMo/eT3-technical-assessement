# Delivery Route Planner

Groups a list of delivery requests into vehicle trips that respect a weight limit, keep each
trip inside a single area, and handle the most urgent deliveries first.

Submitted for the eT3 2026 Software Development Internship technical assignment
([brief](docs/assessment-brief.pdf)).

## The rules it implements

- Each delivery has an ID, an area, a priority, and a package weight.
- A vehicle carries at most **10 kg** per trip, and a trip never exceeds that.
- Deliveries to the same area travel together — a trip never mixes areas.
- **Lower priority numbers are more urgent** and are handled first.
- Every valid delivery appears in exactly one trip.

## Quickstart

Requires Python 3.11 or newer. No third-party runtime dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .

route-planner data/deliveries.sample.csv
```

Other ways to run it:

```bash
route-planner data/deliveries.sample.json      # JSON input
route-planner data/deliveries.edge-cases.csv   # every edge case in one file
route-planner data/deliveries.sample.csv --capacity 20
python -m route_planner data/deliveries.sample.csv
```

Exit code `0` on a successful plan (including an empty one), `1` when the input file cannot
be read or is not a supported format, `2` for invalid command-line arguments.

## Input format

The format is chosen from the file extension. Both accept the same four fields and go
through the same validation, so they can never disagree about what counts as a valid row.

**CSV** (`.csv`) — a header row is required:

```csv
id,area,priority,weight_kg
1,Nasr City,2,4.5
2,Maadi,1,2.0
```

**JSON** (`.json`) — an array of objects with the same keys:

```json
[
  { "id": "1", "area": "Nasr City", "priority": 2, "weight_kg": 4.5 },
  { "id": "2", "area": "Maadi", "priority": 1, "weight_kg": 2.0 }
]
```

| Field | Rule |
| --- | --- |
| `id` | Non-empty and unique within the file |
| `area` | Non-empty after trimming; matched case-insensitively |
| `priority` | A whole number, 1 or greater; lower is more urgent |
| `weight_kg` | A finite number greater than 0 |

Surrounding whitespace is trimmed and a UTF-8 byte-order mark (what Excel writes when you
"Save as CSV") is handled, because those are the two ways a real dispatcher's file breaks.

## Example

```
$ route-planner data/deliveries.sample.csv

Delivery plan — 3 trips, 10 kg vehicle

Trip 1  Maadi  —  5.5/10 kg  (55%, 2 deliveries)
  2     priority 1   2 kg
  5     priority 2   3.5 kg

Trip 2  Zamalek  —  7/10 kg  (70%, 1 delivery)
  4     priority 1   7 kg

Trip 3  Nasr City  —  5.7/10 kg  (57%, 2 deliveries)
  1     priority 2   4.5 kg
  3     priority 3   1.2 kg

Utilisation
  Trips planned        3
  Deliveries assigned  5
  Capacity used        18.2 of 30 kg (61%)
  Spare capacity       11.8 kg
  Under 60% utilised   2 (trip 1 Maadi 55%, trip 3 Nasr City 57%)
```

Rows that could not be planned are listed under a `Not planned` heading with the reason —
run `route-planner data/deliveries.edge-cases.csv` to see all of them.

## How it works

1. **Reject the impossible.** A package heavier than the vehicle can never be carried, so it
   is set aside with a reason instead of being silently dropped.
2. **Bucket by area.** Deliveries are grouped into a dictionary keyed on the normalised area
   name. From this point a trip can only ever contain one area's deliveries — the grouping
   rule is enforced by the data structure rather than by a later check.
3. **Sort inside each bucket** by priority, then by ID. The ID is the tie-break, which makes
   the output deterministic: the same input always produces the same plan.
4. **Pack with first-fit.** Each delivery goes into the first already-open trip for its area
   that still has room; a new trip opens only when none does.
5. **Order the trips.** Areas are ranked by their most urgent delivery, so the vehicle
   carrying the priority-1 work is trip 1. Trips are then numbered from there.

**Why first-fit and not strictly sequential packing?** Sequential (next-fit) packing closes a
trip the moment one package does not fit, which leaves vehicles half empty. First-fit lets a
later, lighter package backfill an earlier trip while the urgent packages still ride in the
earliest trips. In `data/deliveries.edge-cases.csv` this is visible in Nasr City: delivery
103 backfills trip 3 rather than opening a fourth vehicle.

**Where "invalid" ends and "unassignable" begins.** The loader decides whether a *row* is
usable — a weight of `heavy`, a blank area, a repeated ID. The planner decides whether a
valid delivery is *carriable*. That split matters because the second answer is conditional:
a 15 kg package is undeliverable with a 10 kg vehicle but perfectly fine with `--capacity 20`.
Putting the weight check in the loader would bake the vehicle's limit into file parsing.

## Edge cases

| Case | Behaviour | Why |
| --- | --- | --- |
| No deliveries | Prints `No deliveries to plan.`, exits 0 | An empty file is a valid input, not an error |
| Package heavier than the vehicle | Listed under `Not planned` with a reason | Silently dropping it would hide the fact that it cannot be delivered at all |
| Equal priorities | Tie-broken by ID, numerically when IDs are numbers | Determinism, so the same input always gives the same plan |
| Next package would exceed capacity | Try the next open trip for that area; open a new one only if none fits | First-fit; keeps vehicles fuller than closing the trip immediately |
| Malformed row | Skipped and reported with its row number; the rest still plans | One bad line should not cost the dispatcher the whole day's plan |
| Duplicate ID | The later occurrence is rejected | An ID identifies a physical package; keeping both would double-deliver it |
| Area differing by case or padding | Treated as the same area | `Maadi` and ` maadi ` are one place, and real files contain both |
| Unsupported file extension | Clear error, exit 1 | Better to fail fast than to guess the format |

Floating-point weights are compared with a small tolerance. Without it, a load such as
`2.8 + 6.57 + 0.63` — which evaluates to `10.000000000000002` rather than `10.0` — would be
pushed onto a needless extra trip.

## Project layout

```
src/route_planner/
  models.py       Delivery, Trip, Plan, Rejection — the vocabulary of the problem
  loader.py       File in, validated deliveries and rejections out
  planner.py      The grouping and packing algorithm
  reporting.py    A plan rendered as the text report
  cli.py          Argument parsing, exit codes, wiring
data/             Sample inputs, including one file covering every edge case
tests/            One test module per source module
docs/             The original assignment brief
```

`planner.py` is pure: it takes objects and returns objects, reading no files and printing
nothing. That is why its tests need no fixtures and why the algorithm can be reasoned about
on its own.

The package lives under `src/` so the tests run against the *installed* package. A packaging
mistake fails loudly in CI instead of passing by accident because the current directory
happened to be importable.

## Development

```bash
pip install -e ".[dev]"

pytest                  # 52 tests
ruff check .            # lint
ruff format --check .   # formatting
pre-commit install      # run both automatically before each commit
```

GitHub Actions runs the same three commands on Python 3.11, 3.12, and 3.13 for every push
and pull request.

## Extension: the utilisation report

The feature I added is the **Utilisation** block at the end of every plan: how many trips
were planned, how much of the fleet's capacity was actually used, how much was wasted, and
which trips fell below 60% full.

I chose it because "did the plan obey the rules?" and "was it a *good* plan?" are different
questions, and only the first one is testable from the requirements. The packing algorithm is
a heuristic that can leave vehicles half empty (see the next section), and without this report
that cost is invisible — you would see three trips and have no way to know two of them could
have been one. It gives a dispatcher the number they would actually act on, and it gives me
the measurement I would need before changing the algorithm.

## Reasoning

### 1. Explain your solution approach in your own words

I treated it as a grouping problem before a packing problem. The area rule is the hard
constraint, so I bucket deliveries by area first; once that is done, a trip is physically
incapable of mixing areas. Inside each bucket I sort by priority so urgent packages are
placed first, then walk the list putting each package into the first open trip with room,
opening a new trip only when nothing fits. Finally I order the areas by their most urgent
delivery so the trips come out in dispatch order.

Priority therefore controls *order* and area controls *membership*. Priority decides which
package goes first within a bucket and which bucket goes first overall, but it never splits a
bucket. Validation is split the same way: the loader judges whether a row is usable data, the
planner judges whether a valid delivery fits the vehicle.

### 2. What was the most difficult part of the assignment?

Two things, both about drawing a line rather than writing code.

The first was that the area rule and the priority rule appear to contradict each other. Sorted
purely by priority the sample data reads Maadi, Zamalek, Nasr City, Maadi — and any trip built
from that order mixes areas. Deciding that priority orders *within* and *across* groups but
never breaks one is what made both rules satisfiable at the same time, and it took a couple of
attempts to state it that cleanly.

The second was deciding where "invalid" stops and "unassignable" starts. A 15 kg package is
not bad data — it is well-formed and undeliverable, and it stops being undeliverable the moment
you use a bigger vehicle. Realising that it is a property of the *plan* rather than the *file*
is what pushed that check out of the loader and into the planner.

### 3. Are there situations where your algorithm may not produce the best possible grouping?

Yes, and it is worth being precise about why.

This is the classic **bin packing** problem: items of fixed sizes, containers of fixed
capacity, minimise the containers. Bin packing is **NP-hard**. *NP* stands for
*nondeterministic polynomial time* — the class of problems where a proposed answer can be
checked quickly even if finding it is hard. Checking "do these three trips carry everything
under 10 kg each?" is instant; proving no arrangement uses fewer trips would mean examining
every way of splitting the packages, and that number explodes as the input grows. So no
practical program guarantees the minimum. Mine is a heuristic, and here is where it loses.

Take one area, a 10 kg vehicle, and packages arriving in priority order with weights
**6, 3, 5, 5, 4, 7** — 30 kg in total, so three full vehicles are theoretically possible:

| Package | My first-fit, in priority order |
| --- | --- |
| 6 | Trip 1 → 6 kg |
| 3 | Trip 1 → 9 kg |
| 5 | Trip 1 has 1 kg left → Trip 2 → 5 kg |
| 5 | Trip 2 → 10 kg |
| 4 | Trips 1 and 2 are full → Trip 3 → 4 kg |
| 7 | Nothing fits (Trip 3 has 6 kg left) → Trip 4 → 7 kg |

That is **four vehicles**. **First-Fit Decreasing** (FFD) — the same placement rule, but with
the packages sorted heaviest-first before packing — would order them 7, 6, 5, 5, 4, 3 and
produce `[7,3]`, `[6,4]`, `[5,5]`: **three vehicles**.

I did not use FFD, because sorting by weight destroys the priority order. The 7 kg package
might be priority 9 and the 3 kg one priority 1, and FFD would load the least urgent package
first to fill the vehicle better. The brief says urgent deliveries are handled first, so I
traded packing efficiency for the rule I was actually given.

There is a second, larger source of suboptimality: a trip never spans two areas, even when a
vehicle leaves half empty and the next area is a street away. That is correct against the
brief, which has no notion of distance, but a real planner with coordinates would sometimes
merge two neighbouring areas into one trip.

### 4. If the input contained 1,000,000 delivery requests, what part of your solution might become slow or memory-intensive?

Two distinct problems.

**Memory.** `load_deliveries` reads the entire file into a list before planning starts, so a
million `Delivery` objects and their strings sit in RAM at once — on the order of hundreds of
megabytes, none of it released until the run ends. The fix follows from the algorithm itself:
because a trip never spans areas, only one area needs to be in memory at a time. Sort or
bucket the file by area first, then plan and emit one area before reading the next.

**Speed.** First-fit scans the open trips for an area looking for one with room. With `n`
deliveries and `t` open trips that is up to `n × t` comparisons — `O(n·t)`. Concentrate
900,000 deliveries in one area and you have roughly 100,000 open trips and on the order of
10^11 comparisons, which never finishes. The fix is to stop scanning linearly: index the open
trips by remaining capacity. Real weights land on one or two decimal places, so there are only
about a hundred distinct remaining-capacity buckets — "give me any trip with at least 4.5 kg
free" then becomes a lookup instead of a walk.

Everything else is fine at that scale: the sort is `O(n log n)` and the area bucketing is a
single linear pass.

### 5. What would you improve if you had another day?

These are **not implemented** — they are what I would do next.

- **Property-based testing.** I have one test that generates 500 random deliveries and asserts
  the invariants (every delivery placed exactly once, no trip over capacity). With Hypothesis
  that becomes hundreds of generated cases that actively hunt for the input that breaks them,
  rather than one fixed seed.
- **A `--strategy` flag** to run first-fit against first-fit-decreasing on the same input and
  compare them using the utilisation report as the scoreboard. That turns question 3 from an
  argument into a measurement, and would let a dispatcher decide per-run whether to trade
  priority order for a saved vehicle.
- **Streaming the loader** as described in question 4, so the tool survives a file that does
  not fit in memory.
- **A JSON output mode**, so the plan can feed a dispatch system rather than only a terminal.

## Notes on how this was built

I used Claude, Anthropic's AI assistant, to help plan the solution and to brainstorm what
could work and what could go wrong before I settled on an approach. The design, the code, and
the reasoning above are mine to explain and defend, which is why this README spends more space
on *why* than on *what*.

## Licence

MIT — see [LICENSE](LICENSE).
