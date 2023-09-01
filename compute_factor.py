from typing import List

from file_tracking_classes import AuthorTotalKnowledge, AuthorTotalAuthorship

def compute_truck_factor_from_file_authorship(knowledge: int, authored_files: dict[str, int], critical_loss: float = 0.5) -> list[AuthorTotalAuthorship]:
    '''Computes the Truck Factor based on file authorship.

    Args:
        knowledge (int): Total knowledge in the repository.
        authored_files (dict[str, int]): Dictionary mapping authors to the number of files authored.
        critical_loss (float): Critical loss ratio for the Truck Factor calculation.

    Returns:
        list: List of AuthorTotalAuthorship.
    '''
    knowledge_left = knowledge
    sorted_authors = dict(sorted(authored_files.items(), key=lambda item: item[1], reverse=True))
    truck_factor = []
    for author, files_authored in sorted_authors.items():
        truck_factor.append(AuthorTotalAuthorship(author, files_authored, knowledge))
        knowledge_left -= files_authored
        if (knowledge_left / knowledge) < critical_loss:
            return truck_factor
    return truck_factor


def compute_truck_factor_from_knowledge_base(total_knowledge: int, knowledge_base: dict, critical_loss: float = 0.5) -> List[AuthorTotalKnowledge]:
    '''Computes the Truck Factor based on knowledge base.

    Args:
        total_knowledge (int): Total knowledge in the repository.
        knowledge_base (dict): Dictionary mapping owners to their knowledge.
        critical_loss (float): Critical loss ratio for the Truck Factor calculation.

    Returns:
        list: List of AuthorTotalKnowledge.
    '''
    knowledge_left = total_knowledge
    sorted_owners = dict(sorted(knowledge_base.items(), key=lambda item: item[1], reverse=True))
    truck_factor = []
    for owner, knowledge in sorted_owners.items():
        truck_factor.append(AuthorTotalKnowledge(owner, knowledge, total_knowledge))
        knowledge_left -= knowledge
        if (knowledge_left / total_knowledge) <= critical_loss:
            return truck_factor
    return truck_factor