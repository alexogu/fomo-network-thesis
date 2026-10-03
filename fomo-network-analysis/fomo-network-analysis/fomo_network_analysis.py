"""
Fomo Social Trading Network Analysis

Which crypto wallets on Fomo are the most influential, and how does the
structure of Fomo's social trading network reveal which traders occupy the
most central positions?

Pipeline:
    1. Collect the Fomo 30-day leaderboard            (FOMO API)
    2. Collect each sampled trader's following list   (FOMO API)
    3. Build a directed follower -> followed edge list
    4. Validate the edge list
    5. Build a NetworkX directed graph
    6. Calculate in-degree and betweenness centrality
    7. Save the results table and two figures

Usage:
    set FOMO_API_KEY=your_key_here          (Windows cmd)
    export FOMO_API_KEY=your_key_here       (macOS / Linux)

    python fomo_network_analysis.py             # collect data, then analyze
    python fomo_network_analysis.py --skip-collect   # re-run analysis on saved CSV
"""

import argparse
import os
import sys
import time
from datetime import datetime, timezone

import matplotlib

matplotlib.use("Agg")  # save figures without needing a display
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
import requests

BASE_URL = "https://api.fomoapi.io"

DATA_DIR = "data"
FIGURES_DIR = "figures"
TRADERS_CSV = os.path.join(DATA_DIR, "fomo_traders.csv")
EDGES_CSV = os.path.join(DATA_DIR, "fomo_following_edges.csv")
RESULTS_CSV = os.path.join(DATA_DIR, "centrality_results.csv")
NETWORK_PNG = os.path.join(FIGURES_DIR, "fomo_network.png")
TOP_PNG = os.path.join(FIGURES_DIR, "fomo_top_in_degree.png")


# ---------------------------------------------------------------------------
# 1-3. Data collection
# ---------------------------------------------------------------------------

def get_headers():
    api_key = os.getenv("FOMO_API_KEY")
    if not api_key:
        sys.exit(
            "FOMO_API_KEY is not set. Get a free key at https://fomoapi.io/dashboard "
            "and set it as an environment variable before running."
        )
    return {"Authorization": f"Bearer {api_key}"}


def collect_leaderboard(headers, window="30d", limit=50):
    """Return the top `limit` traders from the Fomo leaderboard as a DataFrame."""
    response = requests.get(
        f"{BASE_URL}/v2/leaderboard/{window}",
        headers=headers,
        params={"limit": limit},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()

    # Input validation: confirm the response has the shape we expect
    print("Leaderboard status:", response.status_code)
    print("Leaderboard keys:", list(data.keys()))

    rows = []
    for trader in data["traders"]:
        wallets = trader.get("wallets") or {}
        rows.append({
            "handle": trader.get("handle"),
            "userId": trader.get("userId"),
            "rank": trader.get("rank"),
            "followers": trader.get("followers"),
            "wallet_solana": wallets.get("solana"),
            "wallet_evm": wallets.get("evm"),
            "timestamp": data.get("capturedAt"),
        })

    traders = pd.DataFrame(rows)
    print("Number of traders collected:", len(traders))
    return traders


def extract_following_list(data):
    """Find the list of followed accounts inside a /following response."""
    if isinstance(data, list):
        return data
    for key in ("following", "users", "traders", "data", "results"):
        if isinstance(data.get(key), list):
            return data[key]
    # Fall back to the first value that is a list of objects
    for value in data.values():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return value
    return []


def collect_following(headers, traders, limit=200, pause=0.2, retries=2):
    """Return a follower -> followed edge list for every sampled trader."""
    relationships = []
    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for _, trader in traders.iterrows():
        handle = trader["handle"]
        # The API accepts a handle or a userId; the userId survives renames
        lookup = trader["userId"] if pd.notna(trader["userId"]) else handle
        url = f"{BASE_URL}/v2/users/{lookup}/following"

        data = None
        for attempt in range(retries + 1):
            response = requests.get(
                url, headers=headers, params={"limit": limit}, timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                # A slow live read returns partial results; asking again resumes it
                if data.get("partial") and attempt < retries:
                    time.sleep(3)
                    continue
                break
            if response.status_code == 503 and attempt < retries:
                time.sleep(3)
                continue
            break

        if data is None:
            print("Could not collect:", handle, "- status", response.status_code)
            continue

        followed_accounts = extract_following_list(data)
        for followed in followed_accounts:
            relationships.append({
                "follower": handle,
                "followed": followed.get("handle"),
                "followed_followers": followed.get("followers"),
                "followed_following": followed.get("following"),
                "truncated": bool(data.get("truncated", False)),
                "timestamp": collected_at,
            })

        print(f"{handle}: {len(followed_accounts)} following"
              + (" (truncated by Fomo's limit)" if data.get("truncated") else ""))
        time.sleep(pause)

    edges = pd.DataFrame(relationships)
    print("Number of relationships:", len(edges))
    return edges


# ---------------------------------------------------------------------------
# 4. Input validation
# ---------------------------------------------------------------------------

def validate_edges(edges):
    """Remove missing values, self-follows, and duplicate relationships."""
    print("\n--- Input validation ---")
    print("Missing values:\n", edges[["follower", "followed"]].isnull().sum())

    edges = edges.dropna(subset=["follower", "followed"])
    edges = edges[edges["follower"] != edges["followed"]]

    before = len(edges)
    edges = edges.drop_duplicates(subset=["follower", "followed"])
    print("Duplicate relationships removed:", before - len(edges))

    unique_nodes = set(edges["follower"]) | set(edges["followed"])
    print("Unique nodes:", len(unique_nodes))
    print("Unique edges:", len(edges))
    return edges


# ---------------------------------------------------------------------------
# 5-6. Network construction and centrality
# ---------------------------------------------------------------------------

def build_graph(edges):
    """Directed graph: an edge A -> B means trader A follows trader B."""
    G = nx.DiGraph()
    for _, row in edges.iterrows():
        G.add_edge(row["follower"], row["followed"])

    print("\n--- Network ---")
    print("Nodes:", G.number_of_nodes())
    print("Edges:", G.number_of_edges())
    return G


def calculate_centrality(G):
    """Combine in-degree and betweenness centrality into one results table."""
    degree_results = pd.DataFrame(
        dict(G.in_degree()).items(), columns=["wallet", "in_degree"]
    )
    betweenness_results = pd.DataFrame(
        nx.betweenness_centrality(G).items(), columns=["wallet", "betweenness"]
    )

    results = degree_results.merge(betweenness_results, on="wallet")
    results = results.sort_values(
        ["in_degree", "betweenness"], ascending=False
    ).reset_index(drop=True)
    return results


def add_context(results, edges, traders):
    """Attach API-reported follower counts and wallet addresses for output validation."""
    if "followed_followers" in edges.columns:
        reported = (
            edges.dropna(subset=["followed_followers"])
            .drop_duplicates("followed")
            .set_index("followed")["followed_followers"]
        )
        results["api_followers"] = results["wallet"].map(reported)

    if traders is not None and not traders.empty:
        info = traders.drop_duplicates("handle").set_index("handle")
        results["api_followers"] = results.get(
            "api_followers", pd.Series(index=results.index, dtype=float)
        ).fillna(results["wallet"].map(info["followers"]))
        results["wallet_solana"] = results["wallet"].map(info["wallet_solana"])
        results["wallet_evm"] = results["wallet"].map(info["wallet_evm"])

    return results


# ---------------------------------------------------------------------------
# 7. Visualization
# ---------------------------------------------------------------------------

def plot_network(G, results):
    """Figure 1: the full network, with node size scaled by in-degree."""
    in_degree = dict(G.in_degree())
    top3 = results.head(3)["wallet"].tolist()

    plt.figure(figsize=(12, 8))
    pos = nx.spring_layout(G, seed=42)

    nx.draw_networkx_edges(G, pos, alpha=0.15, width=0.4, arrows=True, arrowsize=5)
    nx.draw_networkx_nodes(
        G, pos,
        node_size=[15 + 12 * in_degree[n] for n in G.nodes()],
        node_color=["#d62728" if n in top3 else "#1f77b4" for n in G.nodes()],
        alpha=0.85,
    )
    nx.draw_networkx_labels(
        G, pos, labels={n: n for n in top3}, font_size=9, font_weight="bold"
    )

    plt.title("Fomo Social Trading Network")
    plt.axis("off")
    plt.savefig(NETWORK_PNG, dpi=300, bbox_inches="tight")
    plt.close()
    print("Saved", NETWORK_PNG)


def plot_top_in_degree(results):
    """Figure 2: the ten traders with the highest in-degree."""
    top10 = results.head(10)

    plt.figure(figsize=(10, 6))
    plt.bar(top10["wallet"], top10["in_degree"])
    plt.xticks(rotation=45, ha="right")
    plt.xlabel("Fomo Trader")
    plt.ylabel("Number of Followers in Sample")
    plt.title("Most Connected Fomo Traders by In-Degree")
    plt.tight_layout()
    plt.savefig(TOP_PNG, dpi=300)
    plt.close()
    print("Saved", TOP_PNG)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Fomo social trading network analysis")
    parser.add_argument("--window", default="30d", choices=["24h", "7d", "30d", "all"],
                        help="Leaderboard window used to sample traders (default: 30d)")
    parser.add_argument("--traders", type=int, default=50,
                        help="Number of leaderboard traders to sample (default: 50)")
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip the API and analyze the saved edge list instead")
    args = parser.parse_args()

    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)

    if args.skip_collect:
        if not os.path.exists(EDGES_CSV):
            sys.exit(f"{EDGES_CSV} not found. Run once without --skip-collect first.")
        edges = pd.read_csv(EDGES_CSV)
        traders = pd.read_csv(TRADERS_CSV) if os.path.exists(TRADERS_CSV) else None
    else:
        headers = get_headers()
        traders = collect_leaderboard(headers, window=args.window, limit=args.traders)
        traders.to_csv(TRADERS_CSV, index=False)

        edges = collect_following(headers, traders)
        if edges.empty:
            sys.exit("No following relationships were collected. Check your API key and credits.")

    edges = validate_edges(edges)
    edges.to_csv(EDGES_CSV, index=False)

    G = build_graph(edges)
    results = calculate_centrality(G)
    results = add_context(results, edges, traders)
    results.to_csv(RESULTS_CSV, index=False)

    print("\n--- Top 10 wallets by in-degree, then betweenness ---")
    print(results.head(10).to_string(index=False))

    print("\n--- Top 10 wallets by betweenness ---")
    print(results.sort_values("betweenness", ascending=False).head(10).to_string(index=False))

    plot_network(G, results)
    plot_top_in_degree(results)

    print("\nDone. Results table saved to", RESULTS_CSV)


if __name__ == "__main__":
    main()
