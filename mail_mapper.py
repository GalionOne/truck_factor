from genericpath import exists
from typing import Tuple
import subprocess
import sys
import os

from difflib import SequenceMatcher

from repository_service import get_authors_of_repo

def map_mail_to_names(mailmap) -> list[str]:
    '''Maps email addresses to corresponding
    names in a given mailmap dictionary.

    Args:
        mailmap (dict): A dictionary where keys are email addresses
        and values are lists of names.

    Returns:
        list: A list of formatted strings representing
        the mapping of email addresses to names.
    '''
    naive_mail_map = []
    for mail in mailmap:
        mailmap[mail].sort(key=len, reverse=True)
        names = mailmap[mail]
        s = f"{names[0]} {mail}"
        if len(names) > 1:
            s += " " 
            s += ' '.join(names[1:])
        naive_mail_map.append(s)
    return naive_mail_map


def format_author_output(authors) -> list[str]:
    '''Processes the output obtained from get_authors_from_git()
    to format the author information.

    Args:
        authors (list): A list of author names and email addresses.

    Returns:
        list: A list of formatted strings representing
        the mapping of email addresses to names.
    '''
    mailmap = {}
    for line in authors:
        split = line.split("|")
        name = split[0]
        email = split[-1]
        if email not in mailmap:
            mailmap[email] = [name]
        else:
            mailmap[email].append(name)
    return map_mail_to_names(mailmap)

def are_they_similar(email1, email2, threshold=90) -> bool:
    return SequenceMatcher(None, email1, email2).ratio() >= threshold

def create_naive_mailmap(path_to_local_repo, path_to_mailmap: str) -> None:
    '''Creates a naive mail map by pairing authors with the same names 
    but different emails and authors with the same emails but different names.

    This method retrieves authors from Git, formats the author output,
    and writes the resulting mail map to the specified file.
    '''
    authors = get_authors_of_repo(path_to_local_repo)
    formatted_author_output = format_author_output(authors)
    with open(path_to_mailmap, "w") as mailmap:
        mailmap.writelines("%s\n" % line for line in formatted_author_output)

def read_mailmap(path: str) -> Tuple[dict, dict]:
    '''Reads a mail map and returns two dictionaries.

    Args:
        path (str): The path to the mail map file.

    Returns:
        tuple: A tuple containing two dictionaries.
            - mail_to_mail (dict): A dictionary mapping mail addresses 
            to the corresponding primary mail address.
            - mail_to_name (dict): A dictionary mapping mail addresses 
            to the corresponding name(s).
    '''
    mail_to_mail = {}
    mail_to_name = {}
    with open(path) as git_mailmap:
        for contributor in git_mailmap:
            if contributor[0] == "#":
                continue
            if contributor[0] == "":
                continue
            if contributor[0] == '\n':
                continue
            proper_name = contributor.split("<")[0].strip()
            tmp_mails = contributor.split("<")
            mails = [s.split(">")[0] for s in tmp_mails if ">" in s]
            proper_mail = mails[0]
            mail_to_name[proper_mail] = proper_name
            for mail in mails[1:]:
                mail_to_mail[mail] = proper_mail
    return mail_to_mail, mail_to_name

def get_mailmap(path_to_local_repo: str, path_to_mailmap: str) -> Tuple[dict, dict]:
    ''''Checks if pre-existing mail map exists.
    
    Args:
        path_to_local_repo (str): The path to the local repository.
        path_to_mailmap (str): The path where a mail map is expected.
    Retuns:
        tuple: A tuple containing two dictionaries.
            - mail_to_mail (dict): A dictionary mapping mail addresses 
            to the corresponding primary mail address.
            - mail_to_name (dict): A dictionary mapping mail addresses 
            to the corresponding name(s).
    '''
    mailmap_path = path_to_mailmap
    if not exists(path_to_mailmap):
        print("No mail map exists. Creating naive mailmap at", path_to_local_repo)
        create_naive_mailmap(path_to_local_repo, path_to_mailmap)
        mailmap_path = os.path.join(path_to_local_repo, '.mailmap')
    return read_mailmap(mailmap_path)
