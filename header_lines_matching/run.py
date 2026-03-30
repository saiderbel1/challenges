import argparse
import random
import time
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache

import pandas as pd


def to_cents(value) -> int:
    """
    Convert a numeric/string price to integer cents safely.
    """
    return int(
        (Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )


def from_cents(value: int) -> float:
    return value / 100.0


def generate_stress_data(
    num_lines: int,
    num_headers: int,
    min_price: int,
    max_price: int,
    min_k: int,
    max_k: int,
    seed: int,
):
    """
    Generate hard-ish test data for the memoized DFS.

    The lines have many repeated prices in a narrow range, which makes
    matching ambiguous and therefore harder.
    """
    random.seed(seed)

    prices = [random.randint(min_price, max_price) for _ in range(num_lines)]

    order_lines = [
        {
            "description": f"Item_{i}",
            "price": float(price),
        }
        for i, price in enumerate(prices)
    ]

    headers = []
    for i in range(num_headers):
        k = random.randint(min_k, max_k)

        # Guaranteed solvable header: sample k prices and sum them
        chosen = random.sample(prices, k)
        total_price = sum(chosen)

        headers.append(
            {
                "id": i + 1,
                "total_price": float(total_price),
                "total_lines": k,
            }
        )

    return pd.DataFrame(headers), pd.DataFrame(order_lines)


def solve_exact_k_subset(lines_df: pd.DataFrame, target_cents: int, k: int):
    """
    Find one subset of exactly k order lines whose prices sum to target_cents.

    Returns:
        (matched_indices, stats_dict)

        matched_indices:
            list of original row indices from lines_df if a solution is found,
            otherwise None.

        stats_dict:
            performance/debug info for stress testing
    """
    start_time = time.perf_counter()

    if k < 0:
        return None, {
            "dfs_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "elapsed_sec": 0.0,
            "n_lines": len(lines_df),
            "target_cents": target_cents,
            "k": k,
            "solved": False,
        }

    if k == 0:
        solved = (target_cents == 0)
        return ([] if solved else None), {
            "dfs_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "elapsed_sec": 0.0,
            "n_lines": len(lines_df),
            "target_cents": target_cents,
            "k": k,
            "solved": solved,
        }

    indexed_lines = []
    for original_idx, row in lines_df.iterrows():
        indexed_lines.append(
            {
                "original_idx": original_idx,
                "description": row["description"],
                "price_cents": to_cents(row["price"]),
            }
        )

    indexed_lines.sort(key=lambda x: x["price_cents"])

    prices = [item["price_cents"] for item in indexed_lines]
    original_indices = [item["original_idx"] for item in indexed_lines]
    n = len(prices)

    prefix = [0] * (n + 1)
    for i in range(n):
        prefix[i + 1] = prefix[i] + prices[i]

    suffix = [0] * (n + 1)
    for i in range(n - 1, -1, -1):
        suffix[i] = suffix[i + 1] + prices[i]

    def min_sum_from(start: int, count: int) -> int:
        if count < 0 or start + count > n:
            return float("inf")
        return prefix[start + count] - prefix[start]

    def max_sum_from(start: int, count: int) -> int:
        if count < 0 or n - start < count:
            return -1
        # Maximum sum from prices[start:] by choosing 'count' largest items
        # is the sum of the last 'count' items in the globally sorted list.
        return suffix[n - count]

    dfs_calls = 0

    @lru_cache(maxsize=None)
    def dfs(start: int, remaining_sum: int, remaining_k: int):
        nonlocal dfs_calls
        dfs_calls += 1

        if remaining_sum == 0 and remaining_k == 0:
            return ()

        if remaining_sum < 0 or remaining_k < 0:
            return None

        if n - start < remaining_k:
            return None

        min_possible = min_sum_from(start, remaining_k)
        if min_possible > remaining_sum:
            return None

        max_possible = max_sum_from(start, remaining_k)
        if max_possible < remaining_sum:
            return None

        prev_price = None

        for i in range(start, n):
            price = prices[i]

            # Skip same-value branches at the same recursion level.
            # Since we only need one valid subset, this is fine.
            if prev_price is not None and price == prev_price:
                continue
            prev_price = price

            if price > remaining_sum:
                break

            tail = dfs(i + 1, remaining_sum - price, remaining_k - 1)
            if tail is not None:
                return (i,) + tail

        return None

    positions = dfs(0, target_cents, k)
    cache_info = dfs.cache_info()
    elapsed_sec = time.perf_counter() - start_time

    stats = {
        "dfs_calls": dfs_calls,
        "cache_hits": cache_info.hits,
        "cache_misses": cache_info.misses,
        "elapsed_sec": elapsed_sec,
        "n_lines": n,
        "target_cents": target_cents,
        "k": k,
        "solved": positions is not None,
    }

    if positions is None:
        return None, stats

    return [original_indices[pos] for pos in positions], stats


def solve_headers_independently(order_header_df: pd.DataFrame, order_lines_df: pd.DataFrame):
    """
    Solve each header independently. Reuses cached subset solutions for repeated
    (target_cents, total_lines) pairs.
    """
    subset_cache = {}
    subset_stats_cache = {}

    matched_orders = []
    header_stats = []

    total_start = time.perf_counter()

    for _, header_row in order_header_df.iterrows():
        order_id = header_row["id"]
        total_price_cents = to_cents(header_row["total_price"])
        total_lines = int(header_row["total_lines"])

        cache_key = (total_price_cents, total_lines)

        if cache_key not in subset_cache:
            matched_indices, stats = solve_exact_k_subset(
                order_lines_df,
                target_cents=total_price_cents,
                k=total_lines,
            )
            subset_cache[cache_key] = matched_indices
            subset_stats_cache[cache_key] = stats
            from_cache = False
        else:
            matched_indices = subset_cache[cache_key]
            stats = subset_stats_cache[cache_key]
            from_cache = True

        header_stats.append(
            {
                "id": order_id,
                "total_price": header_row["total_price"],
                "total_lines": total_lines,
                "from_cache": from_cache,
                "solved": matched_indices is not None,
                "dfs_calls": stats["dfs_calls"],
                "cache_hits": stats["cache_hits"],
                "cache_misses": stats["cache_misses"],
                "elapsed_sec": stats["elapsed_sec"],
            }
        )

        if matched_indices is None:
            print(
                f"No match found for header id={order_id}, "
                f"total_price={header_row['total_price']}, total_lines={total_lines}"
            )
            continue

        matched_lines_df = order_lines_df.loc[matched_indices]

        matched_orders.append(
            {
                "id": order_id,
                "total_price": header_row["total_price"],
                "total_lines": total_lines,
                "order_lines": matched_lines_df.to_dict(orient="records"),
            }
        )

    total_elapsed = time.perf_counter() - total_start

    return matched_orders, pd.DataFrame(header_stats), total_elapsed


def print_solver_summary(header_stats_df: pd.DataFrame, total_elapsed: float):
    if header_stats_df.empty:
        print("\nNo solver stats available.")
        return

    unique_solves = header_stats_df[~header_stats_df["from_cache"]]
    cache_reuses = header_stats_df[header_stats_df["from_cache"]]

    print("\n=== Solver Summary ===")
    print(f"Total headers processed: {len(header_stats_df)}")
    print(f"Unique (target, k) solves: {len(unique_solves)}")
    print(f"Cache reuses: {len(cache_reuses)}")
    print(f"Matched headers: {int(header_stats_df['solved'].sum())}")
    print(f"Unmatched headers: {int((~header_stats_df['solved']).sum())}")
    print(f"Total wall time: {total_elapsed:.6f} sec")

    if not unique_solves.empty:
        print("\n--- Unique Solve Stats ---")
        print(f"Max DFS calls: {int(unique_solves['dfs_calls'].max())}")
        print(f"Mean DFS calls: {unique_solves['dfs_calls'].mean():.2f}")
        print(f"Max solve time: {unique_solves['elapsed_sec'].max():.6f} sec")
        print(f"Mean solve time: {unique_solves['elapsed_sec'].mean():.6f} sec")

        hardest = unique_solves.sort_values(
            by=["dfs_calls", "elapsed_sec"], ascending=False
        ).head(10)

        print("\n--- Top 10 Hardest Unique Solves ---")
        print(hardest.to_string(index=False))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Match order headers to order lines using memoized DFS with pruning."
    )

    parser.add_argument(
        "--mode",
        choices=["read", "generate"],
        required=True,
        help="Whether to read CSVs from disk or generate stress-test data.",
    )

    parser.add_argument(
        "--headers-path",
        default="header_lines_matching/order_headers.csv",
        help="Path to order_headers.csv for reading or saving.",
    )
    parser.add_argument(
        "--lines-path",
        default="header_lines_matching/order_lines.csv",
        help="Path to order_lines.csv for reading or saving.",
    )

    parser.add_argument(
        "--print-head",
        type=int,
        default=5,
        help="How many rows of each dataframe to print.",
    )

    # Generation parameters
    parser.add_argument("--num-lines", type=int, default=250)
    parser.add_argument("--num-headers", type=int, default=30)
    parser.add_argument("--min-price", type=int, default=5)
    parser.add_argument("--max-price", type=int, default=20)
    parser.add_argument("--min-k", type=int, default=6)
    parser.add_argument("--max-k", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)

    return parser.parse_args()


def main():
    args = parse_args()

    if args.mode == "read":
        order_header_df = pd.read_csv(args.headers_path)
        order_lines_df = pd.read_csv(args.lines_path)

        print("Read existing CSV files.")
        print(f"Headers path: {args.headers_path}")
        print(f"Lines path:   {args.lines_path}")

    else:
        order_header_df, order_lines_df = generate_stress_data(
            num_lines=args.num_lines,
            num_headers=args.num_headers,
            min_price=args.min_price,
            max_price=args.max_price,
            min_k=args.min_k,
            max_k=args.max_k,
            seed=args.seed,
        )


    print("\nOrder Header:")
    print(order_header_df.head(args.print_head))

    print("\nOrder Lines:")
    print(order_lines_df.head(args.print_head))

    matched_orders, header_stats_df, total_elapsed = solve_headers_independently(
        order_header_df,
        order_lines_df,
    )

    print("\nMatched Orders:")
    for order in matched_orders[:5]:
        print(order)

    print_solver_summary(header_stats_df, total_elapsed)


if __name__ == "__main__":
    main()