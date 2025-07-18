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

from abc import ABC, abstractmethod


class Context(ABC):
    @abstractmethod
    def save_to_file(self, filename):
        pass

    @abstractmethod
    def load_from_file(self, filename):
        pass

    @property
    def command(self):
        raise NotImplementedError
