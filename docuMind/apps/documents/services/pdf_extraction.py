from typing import IO, Union

import pdfplumber


def extract_pages(source: Union[str, IO[bytes]]) -> list[str]:
    """Extract text per page.

    Accepts a filesystem path or an open binary file object (e.g. a Django
    storage file), so it works with local media and remote object storage alike.
    """
    with pdfplumber.open(source) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]