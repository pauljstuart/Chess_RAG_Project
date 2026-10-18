from bs4 import BeautifulSoup
import pandas as pd
import re


def clean_paragraph(text):
    """
    Basic cleanup before chunking.
    """

    # Remove standalone diagram labels such as "Diag. 13"
    text = re.sub(r"^\s*Diag\.\s*\d+\s*$", "", text)

    # Collapse repeated whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()





def classify_paragraph(text):
    indicators = [
        "Diag.",
        "Diagram ",
        "Q-",
        "K-",
        "Kt-",
        "B-",
        "R-",
        "P-",
        "Qx",
        "Kx",
        "Ktx",
        "Bx",
        "Rx",
        "Px",
    ]

    score = sum(indicator in text for indicator in indicators)

    if score >= 2:
        return "position_commentary"

    return "concept"

def determine_chunk_type(paragraph_types):
    unique_types = set(paragraph_types)

    if unique_types == {"concept"}:
        return "concept"

    if unique_types == {"position_commentary"}:
        return "position_commentary"

    return "mixed"

def merge_broken_paragraphs(paragraphs):
    merged = []

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        if not merged:
            merged.append(paragraph)
            continue

        previous = merged[-1]

        # If previous paragraph doesn't end like a complete sentence,
        # assume it was interrupted by formatting/diagram markup.
        if previous[-1] not in ".!?;:\"”":
            merged[-1] = previous + " " + paragraph
        else:
            merged.append(paragraph)

    return merged

def chunk_paragraphs(paragraphs, target_size=1500):
    chunks = []

    current_text = []
    current_types = []
    current_size = 0

    for paragraph in paragraphs:
        paragraph_type = classify_paragraph(paragraph)
        paragraph_size = len(paragraph)

        if (
            current_text
            and current_size + paragraph_size > target_size
        ):
            chunks.append({
                "chunk_text": "\n\n".join(current_text),
                "content_type": determine_chunk_type(current_types),
                "paragraph_types": current_types.copy()
            })

            current_text = []
            current_types = []
            current_size = 0

        current_text.append(paragraph)
        current_types.append(paragraph_type)
        current_size += paragraph_size

    if current_text:
        chunks.append({
            "chunk_text": "\n\n".join(current_text),
            "content_type": determine_chunk_type(current_types),
            "paragraph_types": current_types.copy()
        })

    return chunks


# --------------------------------------------------
# Parse HTML
# --------------------------------------------------

with open("chess_strategy.html", "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")


rows = []
in_part_1 = False


for heading in soup.find_all("h2"):

    title = heading.get_text(" ", strip=True)

    if title == "PART I":
        in_part_1 = True
        continue

    if title.startswith("PART II"):
        break

    if not in_part_1:
        continue

    if not title.startswith("CHAPTER"):
        continue

    paragraphs = []

    for element in heading.find_all_next():

        if element == heading:
            continue

        if element.name == "h2":
            break

        if element.name == "p":

            text = element.get_text(" ", strip=True)
            text = clean_paragraph(text)

            if text:
                paragraphs.append(text)

    paragraphs = merge_broken_paragraphs(paragraphs)
    rows.append({
        "book": "Chess Strategy",
        "chapter_title": title,
        "paragraphs": paragraphs
    })


df = pd.DataFrame(rows)


# --------------------------------------------------
# Create chunks
# --------------------------------------------------

chunk_rows = []

for _, row in df.iterrows():
    chunks = chunk_paragraphs(row["paragraphs"])

    for i, chunk in enumerate(chunks):
        chunk_rows.append({
            "book": row["book"],
            "chapter_title": row["chapter_title"],
            "chunk_index": i,
            "chunk_text": chunk["chunk_text"],
            "content_type": chunk["content_type"]
        })
chunks_df = pd.DataFrame(chunk_rows)


# pandas boolean filtering
rag_df = chunks_df[
    chunks_df["content_type"].isin(["concept", "mixed"])
].copy()

print("Final RAG chunk count:", len(rag_df))



rag_df.to_csv("chess_strategy_rag.csv", index=False)

# --------------------------------------------------
# Inspect results
# --------------------------------------------------

examples_print = 0

print("--- content type  count ----")


print(chunks_df["content_type"].value_counts())

print("\nCONCEPT EXAMPLES\n")

for _, row in chunks_df[
    chunks_df["content_type"] == "concept"
].head(examples_print).iterrows():

    print(row["chapter_title"])
    print("chunk:", row["chunk_index"])
    print(row["chunk_text"])
    print("-" * 80)


print("\nPOSITION COMMENTARY EXAMPLES\n")

for _, row in chunks_df[
    chunks_df["content_type"] == "position_commentary"
].head(examples_print).iterrows():

    print(row["chapter_title"])
    print("chunk:", row["chunk_index"])
    print(row["chunk_text"])
    print("-" * 80)