import threading
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class FileAuthor:
    '''Contains file name and who wrote it.'''
    file: str
    author_name: str
    author_email: str


@dataclass
class Commit:
    '''Contains the size of the commit, the date and file name.'''
    lines: int
    date: datetime
    file: str


@dataclass
class AuthorCommits:
    '''Contains the name of an author, and the commits they have contributed.'''
    author: str
    commits: List[Commit]

@dataclass
class Contribution:
    entity: str
    contribution: float

@dataclass
class AuthorContribution:
    '''Contains the name of the author, and a list of contributions made by them.'''
    author: str
    contributions: List[Contribution]

@dataclass
class AuthorTotalKnowledge:
    '''Contains the name of the author, 
       the amount of knowledge they have contributed,
       and the total amount of knowledge in the repo.'''
    author: str
    author_contribution: float
    total_knowledge: float

@dataclass
class AuthorTotalAuthorship:
    '''Contains the name of the author,
       the amount of files they have  authored,
       and the total amount of files in the repo.'''
    author: str
    files_authored: int
    total_files: int

class LogsCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._all_logs = []

    def add_logs(self, logs: list[str]):
        with self._lock:
            self._all_logs.extend(logs)
            
    def get_logs(self):
        with self._lock:
            return self._all_logs.copy()