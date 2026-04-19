#!/usr/bin/env python3
"""
Quick start example for using trace tools with differing cases.

This demonstrates:
1. Setting up trace collection infrastructure
2. Running targeted campaign for differing cases
3. Organizing and analyzing traces
"""

# =============================================================================
# PART 1: Setup Trace Infrastructure
# =============================================================================

from trace_manager import TraceManager
import pathlib

print("=" * 80)
print("PART 1: Setting up trace infrastructure")
print("=" * 80)

# Initialize manager
manager = TraceManager()

# Create directory structure
traces_base = manager.create_traces_directory_structure()

# Generate index (shows all cases and their properties)
manager.save_trace_index(traces_base)

# Generate markdown report
manager.generate_trace_report(traces_base / "README.md")

print("\n✓ Infrastructure ready!")
print(f"  - Directory: {traces_base}")
print(f"  - Total cases: {len(manager.differing_df)}")
print(f"  - Became safe: {len(manager.differing_df[manager.differing_df['change_type'].str.contains('False→True')])}")
print(f"  - Became unsafe: {len(manager.differing_df[manager.differing_df['change_type'].str.contains('True→False')])}")

# =============================================================================
# PART 2: Run Targeted Campaign
# =============================================================================

print("\n" + "=" * 80)
print("PART 2: Running targeted campaign (OPTIONAL)")
print("=" * 80)

print("""
To run campaign for only the 30 differing cases:

    cd campaigns/
    python campaign_differing_cases.py --timeout 30 --parallel 4

Options:
  --timeout N       : Timeout per case in seconds (default: 30)
  --parallel N      : Number of parallel runs (default: 1)
  --with-traces     : Collect graph traces (requires GraphViz support)
  --output-dir /path: Custom output directory

After campaign completes, result will be in:
    results/differing_cases_YYYYMMDD_HHMMSS/results.csv
""")

# =============================================================================
# PART 3: Organize Results
# =============================================================================

print("\n" + "=" * 80)
print("PART 3: Trace organization and analysis")
print("=" * 80)

print(f"""
After campaign & trace collection:

1. Copy traces from campaign output:
   cp results/differing_cases_XXX/*.dot traces/raw_dots/

2. Organize by change type:
   manager.organize_traces_by_change_type(
       source_dir=pathlib.Path("results/differing_cases_XXX"),
       dest_dir=pathlib.Path("traces")
   )

3. Convert DOT files to images (optional):
   cd traces/became_safe/
   for f in *.dot; do dot -Tpng "$f" -o "${{f%.dot}}.png"; done
   cd ../became_unsafe/
   for f in *.dot; do dot -Tpng "$f" -o "${{f%.dot}}.png"; done

4. Archive for backup:
   manager.archive_traces()
""")

# =============================================================================
# PART 4: Analysis Examples
# =============================================================================

print("\n" + "=" * 80)
print("PART 4: Case information reference")
print("=" * 80)

print("\nAll differing cases:")
print("-" * 80)

import pandas as pd
df = manager.differing_df[['taskset_position', 'scheduler', 'change_type', 
                           'automaton_depth_original', 'automaton_depth_new']].copy()
df.columns = ['Position', 'Scheduler', 'Change', 'Depth (Old)', 'Depth (New)']
print(df.to_string(index=False))

print(f"\n✓ Total: {len(df)} cases")

# =============================================================================
# BONUS: Comparison with campaign results
# =============================================================================

print("\n" + "=" * 80)
print("BONUS: Comparing traces to campaign results")
print("=" * 80)

print("""
After running the targeted campaign, compare results:

    import pandas as pd
    import pathlib
    
    # Load campaign results
    campaign_results = pd.read_csv("results/differing_cases_XXX/results.csv")
    
    # Merge with original differing cases
    merged = pd.merge(
        manager.differing_df,
        campaign_results,
        on=['taskset_position', 'scheduler'],
        suffixes=('_original', '_campaign')
    )
    
    # Check if campaign agrees with earlier results
    inconsistent = merged[merged['is_safe_original'] != merged['is_safe_campaign']]
    print(f"Inconsistencies: {len(inconsistent)}")
    print(inconsistent)
""")

print("\n" + "=" * 80)
print("✓ All setup complete!")
print("=" * 80)
