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

import re
from typing import Dict

def parse_text(
    text: str, lang: str = "python", all_matches: bool = False
) -> str | list[str]:
    pattern = rf"```{lang}.*?\s+(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)

    if not matches:
        # TODO: user-defined error
        error_message = f"Error: No '{lang}' code block found in the text."
        raise ValueError(error_message)

    if all_matches:
        return matches
    else:
        return matches[0]
    
def parse_reasoning(text: str) -> Dict[str, str]:
    """
    Parses the LLM's output to extract the 'Reasoning' text.
    
    Args:
        text: The full output string from the LLM.
        
    Returns:
        A dictionary with 'reasoning' key.
        
    Raises:
        ValueError: If the Reasoning section is not found in the text.
    """
    # Look for reasoning section that ends with ### Result: or end of text
    reasoning_pattern = r"### Reasoning:\s*(.*?)(?:\s*### Result:|$)"
    reasoning_match = re.search(reasoning_pattern, text, re.DOTALL)
    
    if not reasoning_match:
        raise ValueError("Error: '### Reasoning:' section not found.")
    
    reasoning_text = reasoning_match.group(1).strip()
    
    return {
        "reasoning": reasoning_text
    }
