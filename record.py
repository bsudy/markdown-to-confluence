from dataclasses import dataclass
from enum import Enum
import os
from typing import Optional

INVALID_CHARS = [' ', '!' , '#', '&', '(', ')', '*', ',', '.', ':', ';', '<', '>', '?', '@', '[', ']', '^']

class ArticleState(Enum):
    TO_BE_SYNCED = 'to_be_synced'
    CREATED = 'created'
    SKIPPED = 'skipped'
    SYNCED = 'synced'

@dataclass
class Article:

    # TODO I think 1 of them could be removed
    absolute_path: str
    relative_path: str
    content_path: Optional[str] = None

    space: Optional[str] = None
    confluence_id: Optional[str] = None
    ancestor_id: Optional[str] = None
    page_version: Optional[int] = None

    state: ArticleState = ArticleState.TO_BE_SYNCED 
    is_directory: bool = False

    @property
    def is_markdown(self) -> bool:
        return self.name.endswith('.md')

    @property
    def name(self) -> str:
        return os.path.basename(self.absolute_path)

    @property
    def absolute_director(self) -> str:
        return os.path.dirname(self.absolute_path)

    @property
    def parent(self) -> str:
        return os.path.dirname(self.relative_path)

    @property
    def id_label(self) -> str:
        id_label = 'aid_{}'.format(self.relative_path)
        for invalid_char in INVALID_CHARS:
            id_label = id_label.replace(invalid_char, "_")
        return id_label

    def __repr__(self) -> str:
        return self.relative_path
