#!/usr/bin/env python3

"""
Campaign script for investigating differing schedulability test cases.

This script runs ONLY the 30 cases where is_safe verdicts differ between
two test runs, with optional trace output for debugging.

Usage:
    python campaign_differing_cases.py
    python campaign_differing_cases.py --with-traces
    python campaign_differing_cases.py --output-dir /path/to/results
"""

import datetime
import pathlib
import argparse
import sys
from typing import Optional

import pandas as pd

# Add parent directory to path to import campaign utilities
sys.path.insert(0, str(pathlib.Path(__file__).parent))
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "deps" / "benchkit"))

from benchkit.campaign import CampaignIterateVariables
from benchmarks import MCSBench


def load_differing_cases() -> pd.DataFrame:
    """Load the CSV file containing cases with differing is_safe verdicts."""
    results_dir = pathlib.Path(__file__).parent.parent / "notebooks" / "results"
    csv_file = results_dir / "differing_is_safe_results.csv"
    
    if not csv_file.exists():
        raise FileNotFoundError(
            f"Cannot find differing cases file: {csv_file}\n"
            "Please run the compare_schedulability_results.ipynb notebook first."
        )
    
    df = pd.read_csv(csv_file)
    print(f"Loaded {len(df)} differing cases from {csv_file}")
    print(f"Cases breakdown by change type:")
    print(df['change_type'].value_counts())
    return df


def campaign_differing_cases(
    timeout_seconds: int = 30,
    with_traces: bool = False,
    output_dir: Optional[str] = None,
    parallel: int = 1,
):
    """
    Create and run campaign for differing schedulability cases.
    
    Args:
        timeout_seconds: Timeout for each test case
        with_traces: If True, collect graph traces for each case
        output_dir: Directory to save results (default: ./results)
        parallel: Number of parallel runs (1 = sequential)
    """
    
    # Load differing cases
    differing_df = load_differing_cases()
    
    # Create benchmark instance
    benchmark = MCSBench(timeout_seconds=timeout_seconds)
    
    traces_dir_path: Optional[pathlib.Path] = None

    # Configure output directory
    if output_dir is None:
        output_dir_path = pathlib.Path("results") / f"differing_cases_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        output_dir_path = pathlib.Path(output_dir)

    output_dir_path.mkdir(parents=True, exist_ok=True)

    if with_traces:
        print("[WARNING] Traces will be collected (requires Graph output support)")
        traces_dir_path = output_dir_path / "traces"
        traces_dir_path.mkdir(parents=True, exist_ok=True)

    # Build varying variables from the differing cases
    varying_variables = []
    for _, row in differing_df.iterrows():
        taskset_file = row['taskset_file']
        taskset_position = int(row['taskset_position'])
        scheduler = row['scheduler']
        
        # Constants for these cases
        base_config = {
            "taskset_file": taskset_file,
            "taskset_position": taskset_position,
            "scheduler": scheduler,
            "safe_oracles": [],
            "unsafe_oracles": ["hi-over-demand"],
        }

        use_cases = [
            {
                **base_config,
                "use_case": "EDF-VD (exact)",
                "use_idlesim": True,
                "periodic_tweak": False,
            },
            {
                **base_config,
                "use_case": "EDF-VD (pf)",
                "scheduler": "edfvd",
                "use_idlesim": False,
                "periodic_tweak": True,
            },
        ]

        if traces_dir_path is not None:
            taskset_stem = pathlib.Path(taskset_file).stem
        for use_case in use_cases:
            case_config = {**base_config, **use_case}
            if traces_dir_path is not None:
                case_scheduler = case_config["scheduler"]
                trace_file_name = (
                    f"{taskset_stem}_pos{taskset_position:05d}_{case_scheduler}.dot"
                )
                case_config["graph_output"] = str((traces_dir_path / trace_file_name).resolve())
            varying_variables.append(case_config)
    
    print(f"\nConfigured {len(varying_variables)} test cases")

    # Create campaign
    campaign = CampaignIterateVariables(
        name="differing_cases_investigation",
        benchmark=benchmark,
        nb_runs=1,
        variables=varying_variables,
        constants={},
        debug=False,
        gdb=False,
        enable_data_dir=True,
        continuing=False,
        benchmark_duration_seconds=timeout_seconds,
        results_dir=output_dir_path,
    )
    
    # Run campaigns
    print(f"\nRunning campaigns (parallel={parallel})...")
    print(f"Results will be saved to: {output_dir_path}")
    if parallel != 1:
        print(
            "[WARNING] This benchkit setup runs a single campaign sequentially; "
            "the --parallel flag is currently informational only."
        )
    campaign.run()
    
    # Save campaign information
    info_file = output_dir_path / "campaign_info.txt"
    with open(info_file, 'w') as f:
        f.write("Differing Cases Investigation Campaign\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Generated: {datetime.datetime.now().isoformat()}\n")
        f.write(f"Total cases: {len(varying_variables)}\n")
        f.write(f"Timeout per case: {timeout_seconds}s\n")
        f.write(f"Parallel runs: {parallel}\n")
        f.write(f"Traces collected: {'Yes' if with_traces else 'No'}\n\n")
        f.write("Cases:\n")
        f.write("-" * 60 + "\n")
        for i, var in enumerate(varying_variables, 1):
            f.write(
                f"{i:3d}. {var['taskset_file']:40s} "
                f"pos={var['taskset_position']:5d} {var['scheduler']}\n"
            )
    
    print(f"\n✓ Campaign completed!")
    print(f"✓ Results saved to: {output_dir_path}")
    print(f"✓ Campaign info: {info_file}")
    
    return output_dir_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run campaign for schedulability test cases with differing results"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout per test case in seconds (default: 30)",
    )
    parser.add_argument(
        "--with-traces",
        action="store_true",
        help="Collect graph traces for each case (experimental)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Directory to save results (default: results/differing_cases_YYYYMMDD_HHMMSS)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel runs (default: 1)",
    )
    
    args = parser.parse_args()
    
    campaign_differing_cases(
        timeout_seconds=args.timeout,
        with_traces=args.with_traces,
        output_dir=args.output_dir,
        parallel=args.parallel,
    )
