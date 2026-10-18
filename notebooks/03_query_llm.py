# Databricks notebook source
# MAGIC
# MAGIC %pip install databricks-ai-search
# MAGIC %pip install openai
# MAGIC
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,query the LLM

from databricks.ai_search.client import AISearchClient
from databricks.sdk import WorkspaceClient

from openai import OpenAI
import os

import re




def answer_question(question, return_context=False):

    # -----------------------------
    # 1. Connect to AI Search index
    # -----------------------------

    search_client = AISearchClient(disable_notice=True)

    index = search_client.get_index(
        endpoint_name="chess_endpoint",
        index_name="workspace.chess_rag.chess_rag_index",
    )

    # -----------------------------
    # 2. Retrieve relevant chunks
    # -----------------------------



    results = index.similarity_search(
        query_text=question,
        columns=[
            "chunk_id",
            "book",
            "chapter_title",
            "content_type",
            "chunk_text"
        ],
        num_results=3,
        query_type="hybrid", 
        disable_notice=True

    )


    rows = results["result"]["data_array"]

    # build the RAG context 

    context_parts = []

    for row in rows:
        chunk_id = row[0]
        book = row[1]
        chapter_title = row[2]
        chunk_text = row[4]

        context_parts.append(
            f"""
    SOURCE
    Book: {book}
    Chapter: {chapter_title}
    Chunk ID: {chunk_id}

    {chunk_text}
    """
        )

    context = "\n\n".join(context_parts)

    # this is used to quote the sources later

    source_lines = []

    for i, row in enumerate(rows, start=1):
        book = row[1]
        chapter_title = row[2]
        chunk_id = row[0]

        source_lines.append(
            f"- SOURCE {i}: {book}, {chapter_title}, chunk {int(chunk_id)}"
        )

    sources_text = "\n".join(source_lines)

    # build the prompt 

    prompt = f"""
    You are a chess tutor.

    Answer the user's question using only the supplied source material.

    Rules:
    - Do not use outside knowledge.
    - If the sources do not contain enough information, say so.
    - Cite factual claims using source numbers like [SOURCE 1] or [SOURCE 2].
    - Do not list sources that did not contribute to the answer.

    QUESTION:
    {question}

    SOURCE MATERIAL:
    {context}
    """

    w = WorkspaceClient()

    foundation_model = "system.ai.qwen3-next-80b-a3b-instruct"
    print(f"about to query {foundation_model} ")


    token = w.config.authenticate()["Authorization"].replace("Bearer ", "")

    client = OpenAI(
    api_key=token,
    base_url=f"{w.config.host.rstrip('/')}/ai-gateway/mlflow/v1"
    )

    response = client.chat.completions.create(
    model=foundation_model,
    messages=[
        {
        "role": "user",
        "content": prompt
        }
    ],
    max_tokens=256
    )

    # find what sources were used in the answer


    answer_text = response.choices[0].message.content

    used_source_numbers = sorted(
        set(
            int(n)
            for n in re.findall(r"\[SOURCE (\d+)\]", answer_text)
        )
    )

    source_lines = []

    for i in used_source_numbers:
        row = rows[i - 1]

        source_lines.append(
            f"- SOURCE {i}: {row[1]}, {row[2]}, chunk {int(row[0])}"
        )



    # construct the final answer

    final_answer = (
        answer_text
        + "\n\nSources:\n"
        + "\n".join(source_lines)
    )


    if return_context:
        return final_answer, context

    return final_answer






# COMMAND ----------

question = "Why can unnecessary pawn moves be harmful in the opening?"


answer = answer_question( question )

print( answer )

# COMMAND ----------

# DBTITLE 1,evaluation


test_questions = [
    "Why is control of the centre important in chess?",
    "What is the opposition in a pawn ending?",
    "Why should I avoid moving the same piece several times in the opening?",
    "Why are two bishops often stronger than two knights?",
    "When should the king become active in an endgame?",
    "Why can unnecessary pawn moves be harmful in the opening?"
]

for question in test_questions:

    print("------------------------")
    print( question)
    print("------------------------")
    answer = answer_question( question )

    print( answer )
