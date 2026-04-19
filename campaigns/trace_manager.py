#!/usr/bin/env python3

"""
Utilities for managing traces from differing schedulability test cases.

This module provides:
1. Extract differing cases list from CSV
2. Filter campaign results for differing cases
3. Batch process traces (create, archive, visualize)
4. Compare traces between original and new runs

Usage:
    from trace_manager import TraceManager
    
    manager = TraceManager()
    manager.extract_traces_from_campaign("results/campaign_2026-04-16_12-34")
    manager.archive_traces()
"""

import pathlib
import subprocess
import shutil
from typing import List, Dict, Optional
import pandas as pd
import json
from datetime import datetime


class TraceManager:
    """Manager for collecting and organizing test case traces."""

    def __init__(self, notebook_results_dir: Optional[pathlib.Path] = None):
        """
        Initialize trace manager.
        
        Args:
            notebook_results_dir: Path to notebooks/results directory containing
                                 differing_is_safe_results.csv
        """
        if notebook_results_dir is None:
            notebook_results_dir = pathlib.Path(__file__).parent.parent / "notebooks" / "results"
        
        self.notebook_results_dir = pathlib.Path(notebook_results_dir)
        self.differing_cases_file = self.notebook_results_dir / "differing_is_safe_results.csv"
        self.differing_df = None
        self.traces_dir = pathlib.Path("traces")
        
        if not self.differing_cases_file.exists():
            raise FileNotFoundError(f"Cannot find: {self.differing_cases_file}")
        
        self._load_differing_cases()

    def _load_differing_cases(self) -> None:
        """Load the differing cases CSV."""
        self.differing_df = pd.read_csv(self.differing_cases_file)
        print(f"Loaded {len(self.differing_df)} differing cases")

    def get_case_identifier(self, row: pd.Series) -> str:
        """Get unique identifier for a case."""
        pos = int(row['taskset_position'])
        scheduler = row['scheduler']
        return f"{pos}_{scheduler}"

    def is_differing_case(
        self,
        taskset_position: int,
        scheduler: str,
    ) -> bool:
        """Check if a case is in the differing cases list."""
        matches = self.differing_df[
            (self.differing_df['taskset_position'] == taskset_position) &
            (self.differing_df['scheduler'] == scheduler)
        ]
        return len(matches) > 0

    def get_differing_case_ids(self) -> List[str]:
        """Get list of all differing case identifiers."""
        return [
            self.get_case_identifier(row)
            for _, row in self.differing_df.iterrows()
        ]

    def create_trace_index(self) -> Dict:
        """Create an index of trace files and their metadata."""
        index = {
            "created": datetime.now().isoformat(),
            "differing_case_count": len(self.differing_df),
            "cases": []
        }
        
        for _, row in self.differing_df.iterrows():
            case_id = self.get_case_identifier(row)
            index["cases"].append({
                "id": case_id,
                "taskset_position": int(row['taskset_position']),
                "scheduler": row['scheduler'],
                "change_type": row['change_type'],
                "is_safe_original": bool(row['is_safe_original']),
                "is_safe_new": bool(row['is_safe_new']),
                "depth_original": int(row['automaton_depth_original']),
                "depth_new": int(row['automaton_depth_new']),
            })
        
        return index

    def save_trace_index(self, output_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
        """Save trace index as JSON."""
        if output_dir is None:
            output_dir = self.traces_dir
        
        output_dir = pathlib.Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        index = self.create_trace_index()
        index_file = output_dir / "trace_index.json"
        
        with open(index_file, 'w') as f:
            json.dump(index, f, indent=2)
        
        print(f"✓ Saved trace index to: {index_file}")
        return index_file

    def create_traces_directory_structure(self, base_dir: Optional[pathlib.Path] = None) -> pathlib.Path:
        """Create recommended directory structure for storing traces."""
        if base_dir is None:
            base_dir = self.traces_dir
        
        base_dir = pathlib.Path(base_dir)
        
        # Create subdirectories
        (base_dir / "became_safe").mkdir(parents=True, exist_ok=True)
        (base_dir / "became_unsafe").mkdir(parents=True, exist_ok=True)
        (base_dir / "raw_dots").mkdir(parents=True, exist_ok=True)
        
        print(f"✓ Created trace directory structure at: {base_dir}")
        print(f"  - became_safe/: Cases that became safe (False→True)")
        print(f"  - became_unsafe/: Cases that became unsafe (True→False)")
        print(f"  - raw_dots/: Raw GraphViz dot files")
        
        return base_dir

    def organize_traces_by_change_type(
        self,
        source_dir: pathlib.Path,
        dest_dir: Optional[pathlib.Path] = None,
    ) -> None:
        """
        Organize trace files into subdirectories by change type.
        
        Args:
            source_dir: Directory containing raw trace files
            dest_dir: Destination base directory (default: traces/)
        """
        if dest_dir is None:
            dest_dir = self.traces_dir
        
        dest_dir = pathlib.Path(dest_dir)
        self.create_traces_directory_structure(dest_dir)
        
        source_dir = pathlib.Path(source_dir)
        if not source_dir.exists():
            print(f"⚠️  Source directory does not exist: {source_dir}")
            return
        
        moved_count = 0
        for trace_file in source_dir.glob("*.dot"):
            # Extract case ID from filename
            case_id = trace_file.stem  # Remove .dot extension
            
            # Find matching differing case
            for _, row in self.differing_df.iterrows():
                if self.get_case_identifier(row) == case_id:
                    change_type = row['change_type']
                    if "Became Safe" in change_type:
                        dest_subdir = dest_dir / "became_safe"
                    else:
                        dest_subdir = dest_dir / "became_unsafe"
                    
                    dest_file = dest_subdir / trace_file.name
                    shutil.copy2(trace_file, dest_file)
                    moved_count += 1
                    print(f"  ✓ {trace_file.name} → {dest_subdir.name}/")
                    break
        
        print(f"✓ Organized {moved_count} trace files")

    def archive_traces(
        self,
        traces_dir: pathlib.Path = None,
        archive_name: Optional[str] = None,
    ) -> pathlib.Path:
        """
        Archive trace directory to compressed file.
        
        Args:
            traces_dir: Directory to archive (default: traces/)
            archive_name: Name for archive (default: traces_YYYYMMDD_HHMMSS.tar.gz)
        
        Returns:
            Path to created archive
        """
        if traces_dir is None:
            traces_dir = self.traces_dir
        
        traces_dir = pathlib.Path(traces_dir)
        if not traces_dir.exists():
            print(f"⚠️  Traces directory does not exist: {traces_dir}")
            return None
        
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"traces_{timestamp}.tar.gz"
        
        archive_path = pathlib.Path(archive_name)
        
        try:
            shutil.make_archive(
                archive_path.stem,  # output filename without extension
                'gztar',  # format
                traces_dir.parent,  # base directory
                traces_dir.name  # directory to archive
            )
            print(f"✓ Created archive: {archive_path}")
            return archive_path
        except Exception as e:
            print(f"✗ Failed to create archive: {e}")
            return None

    def generate_trace_report(self, output_file: Optional[pathlib.Path] = None) -> pathlib.Path:
        """
        Generate markdown report summarizing traces.
        
        Args:
            output_file: Where to save report (default: traces/README.md)
        
        Returns:
            Path to generated report
        """
        if output_file is None:
            output_file = self.traces_dir / "README.md"
        
        output_file = pathlib.Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        became_safe = len(self.differing_df[self.differing_df['change_type'].str.contains("False→True")])
        became_unsafe = len(self.differing_df[self.differing_df['change_type'].str.contains("True→False")])
        
        content = f"""# Schedulability Test Case Traces

**Generated:** {datetime.now().isoformat()}

## Summary
- **Total differing cases:** {len(self.differing_df)}
- **Cases that became safe:** {became_safe}
- **Cases that became unsafe:** {became_unsafe}

## Directory Structure
```
traces/
├── became_safe/      - Cases: False → True (previously unsafe, now safe)
├── became_unsafe/    - Cases: True → False (previously safe, now unsafe)
├── raw_dots/         - Original GraphViz dot files
├── trace_index.json  - Metadata index
└── README.md         - This file
```

## Using the Traces

### View a single trace as DOT
```bash
cat traces/became_safe/4985_edfvd.dot
```

### Convert DOT to PNG
```bash
dot -Tpng traces/became_safe/4985_edfvd.dot -o 4985_edfvd.png
```

### Convert all traces to PNG
```bash
for f in traces/became_safe/*.dot; do
  dot -Tpng "$f" -o "${{f%.dot}}.png"
done
```

### Generate graph statistics
```bash
wc -l traces/became_safe/*.dot    # Number of lines (approximates complexity)
ls -lh traces/became_safe/*.dot   # File sizes
```

## Case Details

### Became Safe (False → True)
"""
        
        for _, row in self.differing_df[self.differing_df['change_type'].str.contains("False→True")].iterrows():
            case_id = self.get_case_identifier(row)
            depth_change = int(row['automaton_depth_new']) - int(row['automaton_depth_original'])
            content += (
                f"- **{case_id}**: "
                f"Depth {int(row['automaton_depth_original'])}→{int(row['automaton_depth_new'])} "
                f"({depth_change:+d})\n"
            )
        
        content += f"\n### Became Unsafe (True → False)\n"
        for _, row in self.differing_df[self.differing_df['change_type'].str.contains("True→False")].iterrows():
            case_id = self.get_case_identifier(row)
            depth_change = int(row['automaton_depth_new']) - int(row['automaton_depth_original'])
            content += (
                f"- **{case_id}**: "
                f"Depth {int(row['automaton_depth_original'])}→{int(row['automaton_depth_new'])} "
                f"({depth_change:+d})\n"
            )
        
        with open(output_file, 'w') as f:
            f.write(content)
        
        print(f"✓ Generated report: {output_file}")
        return output_file


if __name__ == "__main__":
    # Example usage
    manager = TraceManager()
    
    # Create directory structure
    manager.create_traces_directory_structure()
    
    # Save index
    manager.save_trace_index()
    
    # Generate report
    manager.generate_trace_report()
    
    print("\n✓ Trace infrastructure ready!")
    print(f"  Differing cases: {len(manager.differing_df)}")
    print(f"  Case IDs: {', '.join(manager.get_differing_case_ids()[:5])}...")
