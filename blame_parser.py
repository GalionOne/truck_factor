import operator
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from file_tracking_classes import Commit, AuthorCommits, AuthorContribution
import constants

def parse_log(blame_log_path: str) -> Dict[str, Commit]:
    '''Parses a blame log from git command "git -C [repository] blame HEAD --incremental -f [fileName]"'''
    shaLineRE = r"[\d\w]{40}"
    authorLineRE = r"author "
    authorEmailLineRE = r"author-mail "
    authorTimeRE = r"author-time "

    commits = defaultdict(list)
    prev = 0
    author = ""
    authorEmail = ""
    timestamp = datetime.utcfromtimestamp(0)
    authors = {}
    #The --incremental blame logs have a sha line starting with the sha of the commit
    # and it ends with an int of how many lines have changed.
    #following the first sha line is the info on the source of the commit.
    #After the first sha line, every commit will be attributed to the current author.
    #When there are no more commits, the previous commit gets attributed to the current author.
    with open(blame_log_path) as log:
        for line in log:
            #If it is a sha line.
            if re.match(shaLineRE, line):
                if prev > 0:
                    commits[authorEmail].append(Commit(prev, timestamp, blame_log_path))          
                prev = int(line.split(' ')[-1])
                continue
            
            if re.match(authorLineRE, line):
                author = " ".join(line.split(" ")[1:])
                continue

            if re.match(authorTimeRE, line):
                timestamp = datetime.utcfromtimestamp(int(line.split(" ")[1]))
            
            if re.match(authorEmailLineRE, line):
                authorEmail = line.split("author-mail ")[-1].split("<")[-1].split(">")[0]
                authors[authorEmail] = author
                continue
        commits[authorEmail].append(Commit(prev, timestamp, blame_log_path))
    return commits



def knowledge_retention_function(t: int, a: float, b: float, beta: float):
    ''' Calculate retention at time t using a power function.

    Args:
        t: Time elapsed since the initial learning.
        a: Asymptotic retention level.
        b: Initial retention level.
        beta: Curvature of the forgetting curve.
    '''
    return a + (1 - a) * b * (1 + t) ** (-beta)


def compute_lines_value(commit: Commit) -> float:
    '''Computes the weight of a commit based on expected knowledge retention'''
    # Knowledge retention is based off of a study by Lee Averell and Andrew Heathcote
    # https://www.sciencedirect.com/science/article/pii/S0022249610001100
    # Constants used in the study: a = 0.19, b = 0.78,  β = 0.68
    timeDelta = constants.INITIAL_TIMESTAMP - commit.date
    asymptote = 0.19
    b = 0.78
    beta = 0.68

    weightFactor = knowledge_retention_function(timeDelta.days, asymptote, b, beta)
    
    return commit.lines * weightFactor


def compute_contribution_value(commits: List[Commit]) -> float:
    '''Takes a list of `commits` and returns their total contribution value'''
    value = 0
    for commit in commits:
        value += compute_lines_value(commit)   
    return value 


def compute_author(author_contributions: Dict[str, AuthorCommits]) -> AuthorContribution:
    '''Takes a dict of authors and their commits and returns the author name and a list of files and their contribution'''
    authorWeight = []
    for author in author_contributions:
        authorWeight.append((author, compute_contribution_value(author_contributions[author]))) 
    author = AuthorContribution(max(authorWeight, key=operator.itemgetter(1))[0], authorWeight)   
    return (author)

def use_mailmap(contributions: Dict[str, AuthorCommits], mail_to_mail: Dict[str, str]) -> Dict[str, AuthorCommits]:
    """Uses the mailmap to group contributions from different identities to the same author"""
    mappedContributions = defaultdict(list)
    for authorMail in contributions:
        if authorMail in mail_to_mail:
            mappedMail = mail_to_mail[authorMail]
            mappedContributions[mappedMail] += contributions[authorMail]
        else:
            mappedContributions[authorMail] += contributions[authorMail]
    return mappedContributions


def compute_knowledge_ownership(blame_log: str, mail_to_mail: Dict[str, str]) -> AuthorContribution:
    '''Computes how much knowledge an author is expected to have about a given project.

    Args:
        blame_log: A blame log from git command "git -C [repository] blame HEAD --incremental -f [fileName]".
        mail_to_mail: A dict of author name and their aliases.'''
    author_contributions = parse_log(blame_log)
    mapped_contributions = use_mailmap(author_contributions, mail_to_mail)
    #Keeping for testing purposes
    #print("-------------------------------------------------")
    #print(type(authorContributions), type(mappedContributions))
    #print("!!!Unmapped contributions", authorContributions)
    #print("### Mapped contributions", mappedContributions)
    #print("-------------------------------------------------")
    return compute_author(mapped_contributions)