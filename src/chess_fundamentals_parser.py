from bs4 import BeautifulSoup
import pandas as pd

# Chunking strategy :
#
# Chess Strategy: Part 1 → chapter → chunks, while retaining the chapter title and preserving diagrams/position context as much as possible.

with open("chess_fundamentals.html", "r", encoding="utf-8") as f:
    html = f.read()

soup = BeautifulSoup(html, "html.parser")


for h2 in soup.find_all("h2"):
    print(h2.get_text(" ", strip=True))

for h3 in soup.find_all("h3"):
    print(h3.get_text(" ", strip=True))

for h4 in soup.find_all("h4"):
    print(h4.get_text(" ", strip=True))
