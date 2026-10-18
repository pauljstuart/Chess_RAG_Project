from bs4 import BeautifulSoup
import pandas as pd

# Chunking strategy :
#
# Chess Strategy: Part 1 → chapter → chunks, while retaining the chapter title and preserving diagrams/position context as much as possible.

with open("chess_strategy.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")


# for h2 in soup.find_all("h2"):
#     print(h2.get_text(" ", strip=True))


# now extract all the heading text
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

    content = []

    for element in heading.find_all_next():
        if element == heading:
            continue

        # stop when we hit another h2
        if element.name == "h2":
            break

        if element.name == "p":
            text = element.get_text(" ", strip=True)
            if text:
                content.append(text)

    rows.append({
        "book": "Chess Strategy",
        "chapter_title": title,
        "text": "\n\n".join(content)
    })

df = pd.DataFrame(rows)

print(df[["chapter_title"]])
print()
print(df.iloc[0]["text"][:1000])

df["char_count"] = df["text"].str.len()

print(df[["chapter_title", "char_count"]])




