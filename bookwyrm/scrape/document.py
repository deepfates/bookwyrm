from bookwyrm.models import Document
from bookwyrm.utils import get_token_count

def create_document(text, source, metadata=None):
    if metadata is None:
        metadata = {}
    return Document(
        text=text,
        source=source,
        metadata=metadata,
        num_files=len(text.split("# ---")),
        num_chars=len(text),
        num_tokens=get_token_count(text)
    )
