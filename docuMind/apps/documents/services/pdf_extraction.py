import pdfplumber


def extract_pages(file_path: str) -> list[str]:
    with pdfplumber.open(file_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]
