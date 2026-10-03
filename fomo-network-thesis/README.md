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
fomo-network-thesis/
│
├── data/
│   ├── nodes.csv    # one row per trader: handle, followers, wallets, in_degree, betweenness
│   └── edges.csv    # one row per following relationship: source follows target
│
├── figures/
│   ├── fomo_network.png
│   └── fomo_top_in_degree.png
│
├── fomo_network_analysis.ipynb
├── requirements.txt
└── README.md
```

The files in `data/` and `figures/` are created when the notebook runs.

## How to run

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. Get a free API key from the [FOMO API dashboard](https://fomoapi.io/dashboard).

3. Open the notebook and run every cell from top to bottom:

   ```
   jupyter notebook fomo_network_analysis.ipynb
   ```

   The first cell asks for the API key. It is typed in at run time, so it is never saved in the notebook.

A run makes 51 API calls (1 leaderboard + 50 following lists), which fits inside the free tier.

## Results

The three most central traders in the sampled network:

| Rank | Fomo Trader | In-Degree | Betweenness |
| --- | --- | --- | --- |
| 1 | _fill in from `data/nodes.csv`_ | | |
| 2 | | | |
| 3 | | | |

![Fomo social trading network](figures/fomo_network.png)

*Figure 1: Each node is a trader and each arrow is a following relationship. Node size reflects in-degree; the three most central traders are highlighted and labeled.*

![Most connected Fomo traders](figures/fomo_top_in_degree.png)

*Figure 2: The ten traders with the most incoming follows within the sample.*

## Validation

- **Input:** the notebook counts missing values in the edge list, removes duplicate relationships, and reports the number of nodes and edges.
- **Output:** `nodes.csv` keeps the follower count Fomo itself reports (`followers`) next to each trader's `in_degree`, so the two can be compared. A high in-degree alongside a very low reported follower count would signal a data or construction problem.
- **AI use:** AI tools were used to help understand NetworkX functions and troubleshoot code. API documentation was verified independently and results were checked against the collected data.

## Limitations

- **The network is a sample.** Only leaderboard traders' following lists are collected, so the results describe the sampled network, not all of Fomo.
- **Only sampled traders have outgoing edges.** Accounts that appear only because someone followed them have no following list of their own in the data. In-degree is therefore "follows received from top traders", and betweenness can only be non-zero for sampled traders.
- **Following lists can be incomplete.** Fomo returns at most 200 followed accounts per trader.
- **The network changes over time.** The data is a snapshot from when the notebook was run.
- **Centrality is not proof of influence.** A central position does not show that a trader actually changed anyone's trading decisions, and it says nothing about profitability.
- **Wallet identity is complicated.** Following relationships belong to Fomo accounts, not directly to wallets. This is a network of trader identities associated with wallets, not a complete on-chain graph.

## Data source

Data comes from the [FOMO API](https://fomoapi.io/docs), an independent, unofficial developer service that is not affiliated with fomo.family.

- `GET /v2/leaderboard/{window}` — ranked traders with `handle`, `userId`, `followers`, and `wallets`
- `GET /v2/users/{handle}/following` — the accounts a trader follows
