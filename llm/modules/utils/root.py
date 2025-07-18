"""
Copyright (c) 2025 WindyLab of Westlake University, China
All rights reserved.

This software is provided "as is" without warranty of any kind, either
express or implied, including but not limited to the warranties of
merchantability, fitness for a particular purpose, or non-infringement.
In no event shall the authors or copyright holders be liable for any
claim, damages, or other liability, whether in an action of contract,
tort, or otherwise, arising from, out of, or in connection with the
software or the use or other dealings in the software.
"""

import datetime
from pathlib import Path
import argparse # Assuming you use argparse

def get_project_root() -> Path:
    """Search upwards to find the project root directory."""
    current_path = Path.cwd()
    while True:
        # Simplified the condition for clarity
        if (current_path / ".git").exists() or (current_path / ".project_root").exists():
            return current_path
        parent_path = current_path.parent
        if parent_path == current_path:
            return Path.cwd() # Fallback to current dir
        current_path = parent_path

class PathManager:
    """
    Manages all directory paths for a specific, single execution run.
    """
    def __init__(self, task_name: str, base_results_dir: str = "UserInterface/results", formatted_date: str = ''):
        """
        Initializes and creates all necessary paths for the run.
        
        Args:
            task_name: The name of the task, used for creating the output folder.
            base_results_dir: The root directory where all results are stored.
            ablation_path: Optional subfolder for ablation studies.
        """
        self.project_root: Path = get_project_root()
        self.workspace_root: Path = (
            self.project_root
            / base_results_dir
            / task_name
            / formatted_date
        )
        
        self.data_root: Path = self.workspace_root / "data"
        
        # Ensure the directories exist
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.data_root.mkdir(exist_ok=True)