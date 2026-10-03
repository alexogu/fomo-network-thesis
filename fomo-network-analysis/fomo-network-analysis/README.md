# Fomo Social Trading Network Analysis

A network analysis of who follows whom on [Fomo](https://fomo.family), the social crypto trading platform.

**Research question:** Which crypto wallets on Fomo are the most influential, and how does the structure of Fomo's social trading network reveal which traders occupy the most central positions?

**Stakeholder:** a crypto researcher or trader who wants to understand how attention is distributed across Fomo, and which accounts are worth monitoring when studying activity and information flow on the platform.

This project measures *network influence*, not trading ability. Fomo's leaderboard ranks traders by performance; this analysis looks at a different kind of information — who traders choose to watch.

## Method

| Step | What happens |
| --- | --- |
| 1. Sample | Take the top 50 traders from Fomo's 30-day leaderboard |
| 2. Collect | Request each trader's following list from the FOMO API |
| 3. Edge list | Record each relationship as `follower → followed` |
| 4. Validate | Drop missing values, self-follows, and duplicate relationships |
| 5. Graph | Build a directed graph with NetworkX |
| 6. Centrality | Calculate in-degree and betweenness centrality |
| 7. Visualize | Draw the network and chart the most-followed traders |

**Nodes** are Fomo trader accounts, each associated with a Solana and an EVM wallet.
**Edges** are directed: `A → B` means trader A follows trader B.

**Influence** is defined by two measures:

- **In-degree** — how many traders in the sample follow this account.
- **Betweenness centrality** — how often this account sits on the shortest path between two other accounts, i.e. how much it connects otherwise separate parts of the network.

## Repository structure

```
fomo-network-analysis/
│
├── data/
│   ├── fomo_traders.csv            # sampled leaderboard traders + wallets
│   ├── fomo_following_edges.csv    # follower → followed edge list
│   └── centrality_results.csv      # in-degree + betweenness per trader
│
├── figures/
│   ├── fomo_network.png
│   └── fomo_top_in_degree.png
│
├── fomo_network_analysis.py
├── requirements.txt
└── README.md
```

The files in `data/` and `figures/` are created when the script runs.

## How to run

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Get a free API key from the [FOMO API dashboard](https://fomoapi.io/dashboard) and set it as an environment variable.

   Windows (Command Prompt):
   ```
   set FOMO_API_KEY=your_key_here
   ```

   macOS / Linux:
   ```
   export FOMO_API_KEY=your_key_here
   ```

3. Run the analysis:

   ```
   python fomo_network_analysis.py
   ```

A default run makes 51 API calls (1 leaderboard + 50 following lists), which fits well inside the free tier.

Options:

| Flag | Meaning |
| --- | --- |
| `--traders 100` | Sample more (or fewer) leaderboard traders. Maximum 150. |
| `--window 7d` | Use a different leaderboard window: `24h`, `7d`, `30d`, or `all`. |
| `--skip-collect` | Skip the API and re-run the analysis on the saved edge list. |

## Results

The three most central traders in the sampled network:

| Rank | Fomo Trader | In-Degree | Betweenness |
| --- | --- | --- | --- |
| 1 | _fill in from `data/centrality_results.csv`_ | | |
| 2 | | | |
| 3 | | | |

![Fomo social trading network](figures/fomo_network.png)

*Figure 1: Each node is a trader and each arrow is a following relationship. Node size reflects in-degree; the three most central traders are highlighted and labeled.*

![Most connected Fomo traders](figures/fomo_top_in_degree.png)

*Figure 2: The ten traders with the most incoming follows within the sample.*

## Validation

- **Input:** the script prints the API status code and response keys, counts missing values, removes duplicate and self-referencing edges, and reports the number of unique nodes and edges.
- **Output:** `centrality_results.csv` includes an `api_followers` column — the follower count Fomo itself reports — so each trader's in-degree can be compared against it. A high in-degree alongside a very low reported follower count would signal a data or construction problem.
- **AI use:** AI tools were used to help understand NetworkX functions and troubleshoot code. API documentation was verified independently and results were checked against the collected data.

## Limitations

- **The network is a sample.** Only leaderboard traders' following lists are collected, so the results describe the sampled network, not all of Fomo.
- **Only sampled traders have outgoing edges.** Accounts that appear only because someone followed them have no following list of their own in the data. In-degree is therefore "follows received from top traders", and betweenness can only be non-zero for sampled traders.
- **Following lists can be incomplete.** Fomo returns at most 200 followed accounts per trader. Affected rows are flagged in the `truncated` column of the edge list.
- **The network changes over time.** The data is a snapshot from when it was collected (see the `timestamp` column).
- **Centrality is not proof of influence.** A central position does not show that a trader actually changed anyone's trading decisions, and it says nothing about profitability.
- **Wallet identity is complicated.** Following relationships belong to Fomo accounts, not directly to wallets. This is a network of trader identities associated with wallets, not a complete on-chain graph.

## Data source

Data comes from the [FOMO API](https://fomoapi.io/docs), an independent, unofficial developer service that is not affiliated with fomo.family.

- `GET /v2/leaderboard/{window}` — ranked traders with `handle`, `userId`, `followers`, and `wallets`
- `GET /v2/users/{handle}/following` — the accounts a trader follows
