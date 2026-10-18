# Databricks notebook source
# MAGIC
# MAGIC %pip install databricks-ai-search
# MAGIC %pip install openai
# MAGIC
# MAGIC dbutils.library.restartPython()

# COMMAND ----------


from databricks.ai_search.client import AISearchClient

client = AISearchClient()

index = client.get_index(
    endpoint_name="chess_endpoint",
    index_name="workspace.chess_rag.chess_rag_index"
)


# COMMAND ----------

results = index.similarity_search(
    query_text="Why is control of the centre important in chess?",
    columns=[
        "chunk_id",
        "book",
        "chapter_title",
        "content_type",
        "chunk_text"
    ],
    num_results=5,
    query_type="hybrid"
)

results

# COMMAND ----------

queries = [
    "Why is control of the centre important in chess?",
    "What is the opposition in a pawn ending?",
    "Why should I avoid moving the same piece several times in the opening?"
]


for     query in queries:
    print("-----------")
    print( f"--- {query} ---------")
    results = index.similarity_search(
    query_text=query,
    columns=[
        "chunk_id",
        "book",
        "chapter_title",
        "content_type",
        "chunk_text"
    ],
    num_results=5,
    query_type="hybrid"
    )
    print(results)
    print(" ")