from datetime import datetime
import os
import sys
import subprocess
from typing import Set, Tuple
from genericpath import exists

from git import Repo


def clone_from_git(path_to_git_repo: str, local_path_to_git_repo: str) -> None:
    '''Clones the Git repository specified in the settings to the local path.'''
    Repo.clone_from(path_to_git_repo, local_path_to_git_repo)


def get_git_file_paths(path_to_repo: str) -> Set[str]:
    '''Retrieves the file paths in the Git repository.'''
    repo = Repo(path_to_repo)
    try:
        result = repo.git().ls_tree('-r', '--name-only', 'HEAD')
    except Exception as e:
        print(e)
    file_paths = result.split('\n')
    return set(file_paths)


def create_git_blame_log(path_to_repo: str, local_logs_path: str, file_name: str) -> str:
    '''Creates a Git blame log for the given file and returns the path to the blame log'''
    #print("Generating blame log for:", file_name)
    repo = Repo(path_to_repo)
    path_to_log = os.path.join(local_logs_path, f"{file_name}.log")
    path_to_log_dir = os.path.dirname(path_to_log)
    if not exists(path_to_log_dir):
        #print('running os mkdir:', path_to_log_dir)
        try:
            os.makedirs(path_to_log_dir)
        except Exception as e:
            print(e)
    if not exists(path_to_log):
        result = repo.git().blame('HEAD', '--incremental', f=file_name)
        with open(path_to_log, 'w') as log:
            try:
                log.write(result)
            except Exception as e:
                print(e)
        #print("done for:", file_name)
    #else:
        #print("log already exists:", path_to_log)
    return path_to_log


def get_last_date_written_to(path_to_repo: str, file_path: str) -> datetime:
    '''Retrieves the last date written to the given file in the Git repository.'''
    repo = Repo(path_to_repo)
    result = repo.git().log(file_path, n='1', date='unix')
    result_date = int(result.split('\n')[2].split(' ')[-1])
    return datetime.utcfromtimestamp(result_date)

def get_authors_of_repo(path_to_repo: str) -> set[str]:
    '''Retrieves authors' names and email addresses
    from a Git repository's commit history.

    Args:
        path_to_repo (str): The path to the local repository.
    Returns:
        set: A set of strings representing the authors'
        names and email addresses in the format "name|<email>".
    '''
    repo = Repo(path_to_repo)
    query_result = repo.git().log(format=f'%an|<%ae>')
    return set(query_result.split('\n'))