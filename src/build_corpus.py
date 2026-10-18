

import pandas as pd

strategy_df = pd.read_csv("chess_strategy_rag.csv")
fundamentals_df = pd.read_csv("chess_fundamentals_rag.csv")

combined_df = pd.concat(
    [strategy_df, fundamentals_df],
    ignore_index=True
)

combined_df["chunk_id"] = range(len(combined_df))

print("Total corpus chunks:", len(combined_df))

combined_df.to_csv("chess_rag_corpus.csv", index=False)

