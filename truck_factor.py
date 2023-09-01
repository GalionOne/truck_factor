"""
Usage:
    truck_factor.py clone-repo [generate-blame-logs] [compute-truck-factor] --git-repo=<git-repo> --local-git-repo=<local-git-repo> --local-logs-path=<local-logs-path> --excluded-files=<excluded-files> --included-files=<included-files> --mailmap-path=<mailmap>
    truck_factor.py generate-blame-logs [compute-truck-factor] --local-git-repo=<local-git-repo> --local-logs-path=<local-logs-path> --excluded-files=<excluded-files> --included-files=<included-files> --mailmap-path=<mailmap>
    truck_factor.py compute-truck-factor --local-git-repo=<local-git-repo> --local-logs-path=<local-logs-path> --mailmap-path=<mailmap>

Arguments:
    clone-repo                          Clones the git repo to the local folder
    generate-blame-logs                 Generates the needed blame logs
    copmute-truck-factor                Computes the truck factor using file authorship and knowledge ownership
    --git-repo=<git-repo>               Git repository path
    --local-git-repo=<local-git-repo>   Local Git repository path.
    --local-logs-path=<local-logs-path> Local logs path
    --excluded-files=<excluded-files>   Excluded file extensions separated by ','
    --included-files=<included-files>   Included file extensions separated by ','
    --mailmap-path=<mailmap>            Path to the mailmap to be used. If not provided, a naive mailmap will be created
"""
import os
import shutil
import math
import multiprocessing
import itertools
from typing import Set, Tuple
from threading import Thread

from docopt import docopt

import repository_service as RS
import blame_parser as BP
import compute_factor as CF
import mail_mapper as MM
from file_tracking_classes import Contribution, AuthorTotalAuthorship, AuthorTotalKnowledge, LogsCollector


def clone_repo(path_to_git_repo: str, local_path_to_git_repo: str) -> None:
    '''Clone the specified Git repository to the local directory.

    Args:
        path_to_git_repo (str): The path of the Git repository to clone.
        local_path_to_git_repo (str): The path the repository will be clones to.
    '''
    print("Cloning repo:", path_to_git_repo)
    RS.clone_from_git(path_to_git_repo, local_path_to_git_repo)

def chunks(lst: list, n: int):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def generate_blame_logs(local_path_to_git_repo: str, local_logs_path: str, excluded_files: Set[str], included_files: Set[str]) -> list[str]:
    '''Generate blame logs for the files in the local Git repository and returns a list of paths to the logs.
        included_files take priority over excluded files e.g. included_files is not empty, evety other extension will be excluded.

    Args:
        local_path_to_git_repo (str): The path to the local Git repository.
        local_logs_path (str): The path to the directory where logs will be stored.
        excluded_files (Set[str]): A set of file extensions to exclude from blame logs.
        included_files (Set[str]): A set of file extensions to include in blame logs.

    Returns:
        list[str]: A list of paths to blame logs,
    '''  
    omitted_extenstions = set([])
    print("Getting file paths")
    files = RS.get_git_file_paths(local_path_to_git_repo)
    path_to_blame_logs = LogsCollector()
    
    print("Generating blame logs")
    def process_file(file: str) -> str:
        file_extension = file.split(".")[-1]
        if file_extension.find("/") + file_extension.find("\\") >= 0:
            file_extension = "file"
        if file_extension in included_files:
            return RS.create_git_blame_log(local_path_to_git_repo, local_logs_path, file)
        #elif not included_files and file_extension not in excluded_files:
        #    return RS.create_git_blame_log(local_path_to_git_repo, local_logs_path, file)    
        
        omitted_extenstions.add(file_extension)
        return None
    
    def process_list(arg_files: list[str], logs_list: list[str]):
        paths = []
        for file in arg_files:
            paths.append(process_file(file))
        path_to_blame_logs.add_logs(paths)
    
    file_chunks = list(chunks(list(files), math.ceil(len(files)/multiprocessing.cpu_count())))
    threads = [Thread(target=process_list, args=(file_chunks[index], path_to_blame_logs)) for index in range(len(file_chunks))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    if omitted_extenstions:
        print("File extensions omitted:", omitted_extenstions)
        
    return path_to_blame_logs.get_logs()


def map_add_or_increment_knowledge(knowledge_base: dict, file_knowledge_base: list[Contribution]):
    '''Helper method which keeps track of the knowledge contributions made by each author'''
    for (author, knowledge) in file_knowledge_base:
        if author not in knowledge_base:
            knowledge_base[author] = knowledge
        else:
            new_weight = knowledge_base[author] + knowledge
            knowledge_base[author] = new_weight

def map_add_or_increment_authorship(auhtored_files: dict, author):
    '''Helper method which keeps track of the files authored by each author'''
    if author not in auhtored_files:
        auhtored_files[author] = 1
    else:
        auhtored_files[author] += 1


def compute_ownership(path_to_local_repo: str, path_to_blame_logs: list[str], path_to_mailmap: str) -> Tuple[dict[str, int], dict[str, float]]:
    '''Computes both the authors of each file, and the knowledge authorship, based on the blame logs.

    Args:
        path_to_local_repo (str): The path to the local repository.
        path_to_blame_logs (lis[str]): A list containing the paths for the blame logs. 
        path_to_mailmap (str): The path to the mailmap.
    
    Returns:
        Touple (dict[str, int], dict[str, float]): The first dict is [author, files_authored].
                                                   The second dict is [author, knowledge_authored].
    '''
    authored_files = {}
    knowledge_base = {}

    mail_to_mail, _ = MM.get_mailmap(path_to_local_repo, path_to_mailmap)
    print("Parsing blame logs")
    for file in path_to_blame_logs:
        author_contributions = BP.compute_knowledge_ownership(file, mail_to_mail)
        author = author_contributions.author
        file_knowledge_base = author_contributions.contributions
        #I am ignoring these potential cases, since the knowledge does not belong to anyone
        map_add_or_increment_authorship(authored_files, author)
        map_add_or_increment_knowledge(knowledge_base, file_knowledge_base)
    
    return (authored_files, knowledge_base)

def compute_knowlede_authorship(path_to_local_repo: str, path_to_blame_logs: list[str], path_to_mailmap: str) -> None:
    '''Computes the authorship of the knowledge in the repository
    
    Args:
        path_to_local_repo (str): The path to the local repository.
        path_to_blame_logs (lis[str]): A list containing the paths for the blame logs. 
        path_to_mailmap (str): The path to the mailmap.
    '''
    knowledge_base = {}
    mail_to_mail, _ = MM.get_mailmap(path_to_local_repo, path_to_mailmap)

    print("Parsing blame logs")
    for file in path_to_blame_logs:
        author_contributions = BP.compute_knowledge_ownership(file, mail_to_mail)
        file_knowledge_base = author_contributions.contributions
        map_add_or_increment_knowledge(knowledge_base, file_knowledge_base)
    
    return knowledge_base


def compute_truck_factor(knowledge_base: dict[str, float], authored_files: dict[str, int]) -> Tuple[list[AuthorTotalAuthorship], list[AuthorTotalKnowledge]]:
    '''Computes two truck factors, one using file authorship,
       and another using knowledge authorship.
       
    Args: 
        knowledge_base (dict[str, float]): A dictionary containing the knowledge base authorship.
        authored_files (dict[str, int]): A dictionary containing the file authorship.
    
    Returns:
        Touple(list[AuthorTotalAuthorship], list[AuthorTotalKnowledge])
    '''
    total_files = sum(authored_files.values())
    total_knowledge_base = sum(knowledge_base.values())
    file_tf = CF.compute_truck_factor_from_file_authorship(total_files, authored_files)
    knowledge_tf = CF.compute_truck_factor_from_knowledge_base(total_knowledge_base, knowledge_base)
    
    return (file_tf, knowledge_tf)

def print_truck_factor_results(file_truck_factor: list[AuthorTotalAuthorship] = [],
                               knowledge_truck_factor: list[AuthorTotalKnowledge] = []) -> None:
    if (len(file_truck_factor)):
        print("========================")
        print("Total files:", file_truck_factor[0].total_files)
        print("File author TF:", len(file_truck_factor))
        for author in file_truck_factor:
            print(author.author, author.files_authored, author.files_authored / author.total_files)
    if (len(knowledge_truck_factor)):
        print("========================")
        print("Total Knowledge Base:", knowledge_truck_factor[0])
        print("Knowledge base TF:", len(knowledge_truck_factor))
        for author in knowledge_truck_factor:
            print(author.author, author.author_contribution, author.author_contribution / author.total_knowledge)

def run(arguments: dict) -> None:
    path_to_git_repo = (arguments["--git-repo"])
    local_path_to_git_repo = "".join(arguments["--local-git-repo"])
    local_logs_path = "".join(arguments["--local-logs-path"])
    excluded_files = arguments["--excluded-files"]
    if excluded_files:
        excluded_files = excluded_files.split(',')
    included_files = arguments["--included-files"]
    if included_files and not isinstance(included_files, list) :
        included_files = included_files.split(',')
    path_to_mailmap = "".join(arguments["--mailmap-path"])
    
    if  arguments["clone-repo"]:
        if os.path.exists(local_path_to_git_repo):
            print("Deleting local repo:", local_path_to_git_repo)
            shutil.rmtree(local_path_to_git_repo)
        clone_repo(path_to_git_repo, local_path_to_git_repo)
    if arguments["generate-blame-logs"]:
        logs = generate_blame_logs(local_path_to_git_repo, local_logs_path, excluded_files, included_files)
    if arguments["compute-truck-factor"]:
        dir_info = os.walk(local_logs_path)
        blame_logs = []
        for (path, _, logs) in dir_info:
            for log in logs:
                blame_logs.append(os.path.abspath(os.path.join(path, log)))
        authored_files, knowledge_base = compute_ownership(local_path_to_git_repo, blame_logs, path_to_mailmap)
        file_truck_factor, knowledge_truck_factor = compute_truck_factor(knowledge_base, authored_files)
        print_truck_factor_results(file_truck_factor, knowledge_truck_factor)

def main():
    arguments = docopt(__doc__)
    run(arguments)

if __name__ == "__main__":
    main()