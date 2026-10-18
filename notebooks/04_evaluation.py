# Databricks notebook source
# MAGIC
# MAGIC %pip install databricks-ai-search
# MAGIC %pip install openai
# MAGIC
# MAGIC dbutils.library.restartPython()

# COMMAND ----------

# DBTITLE 1,answer_question function
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


# COMMAND ----------

# DBTITLE 1,Extended Evaluation
evaluation_set = [
    {
        "question": "Why is control of the centre important in chess?",
        "expected_facts": [
            "centre control helps secure the initiative",
            "centre control supports successful attacks",
            "centre control gives pieces more room to operate"
        ]
    },
    {
        "question": "What is the opposition in a pawn ending?",
        "expected_facts": [
            "the kings oppose each other on the same rank, file, or diagonal",
            "close opposition has one square between the kings",
            "the player who moved last has the close opposition",
            "opposition is important in king and pawn endings"
        ]
    },
    {
        "question": "Why should I avoid moving the same piece several times in the opening?",
        "expected_facts": [
            "repeated moves can lose time",
            "rapid development is important",
            "other pieces should be brought into play"
        ]
    },
    {
        "question": "Why can unnecessary pawn moves be harmful in the opening?",
        "expected_facts": [
            "unnecessary pawn moves can lose time",
            "development should be prioritised",
            "only pawn moves that help development are generally desirable"
        ]
    },
    {
        "question": "Why are two bishops often stronger than two knights?",
        "expected_facts": [
            "two bishops control squares of both colours",
            "bishops have long-range mobility",
            "the value of knights can decrease as pieces are exchanged"
        ]
    },
    {
        "question": "When should the king become active in an endgame?",
        "expected_facts": [
            "the king becomes more active after pieces have been exchanged",
            "king activity becomes important in the endgame"
        ]
    },
    {
        "question": "Why is rapid development important in the opening?",
        "expected_facts": [
            "pieces should be brought into play quickly",
            "development improves activity",
            "wasting moves can give the opponent the initiative"
        ]
    },
    {
        "question": "Why is it useful to develop knights before bishops?",
        "expected_facts": [
            "knights can often be developed naturally early",
            "bishop placement may depend on the pawn structure",
            "development should be efficient"
        ]
    },
    {
        "question": "Why should you avoid blocking your own pieces in the opening?",
        "expected_facts": [
            "blocking pieces reduces their activity",
            "development becomes slower",
            "a cramped position can result"
        ]
    },
    {
        "question": "Why are connected central pawns strong?",
        "expected_facts": [
            "central pawns support each other",
            "they help control important central squares",
            "their advance can influence the direction of the game"
        ]
    },
    {
        "question": "What is meant by losing a move in the opening?",
        "expected_facts": [
            "a move that does not help reach the desired position",
            "using more moves than necessary wastes time",
            "wasted moves can delay development"
        ]
    },
    {
        "question": "Why is the initiative important?",
        "expected_facts": [
            "the initiative allows a player to direct the course of play",
            "centre control can help secure the initiative"
        ]
    },
    {
        "question": "Why can exchanging pieces be useful when you have an advantage?",
        "expected_facts": [
            "exchanges can simplify the position",
            "a favourable endgame can make an advantage easier to convert"
        ]
    },
    {
        "question": "Why is knowledge of simple endgames important?",
        "expected_facts": [
            "simple endgames provide positions where the result can be calculated",
            "knowledge of elementary endings helps guide earlier decisions"
        ]
    },
    {
        "question": "Why should opening moves contribute to development?",
        "expected_facts": [
            "development should be completed efficiently",
            "moves that do not contribute can waste time",
            "active pieces improve coordination"
        ]
    }
]


results = []

for item in evaluation_set:
    question = item["question"]

    answer = answer_question(question)

    results.append({
        "question": question,
        "expected_facts": item["expected_facts"],
        "answer": answer
    })


import pandas as pd

evaluation_df = pd.DataFrame(results)

display(evaluation_df)



# COMMAND ----------

# DBTITLE 1,LLM as Judge Function
import json
from databricks.sdk import WorkspaceClient

from openai import OpenAI

def judge_answer(question, expected_facts, answer, context):

    judge_prompt = f"""
You are evaluating a RAG-based chess tutoring system.

Evaluate the generated answer using ONLY:
1. the expected facts
2. the retrieved source material

QUESTION:
{question}

EXPECTED FACTS:
{chr(10).join("- " + fact for fact in expected_facts)}

RETRIEVED SOURCE MATERIAL:
{context}

GENERATED ANSWER:
{answer}

Score the answer from 0 to 2 on each criterion:

CORRECTNESS
2 = factually correct
1 = partially correct or contains a minor error
0 = substantially incorrect

GROUNDEDNESS
2 = all substantive claims are supported by the retrieved sources
1 = mostly grounded, but contains some unsupported claims
0 = contains significant unsupported or contradictory claims

COMPLETENESS
2 = covers nearly all important expected facts
1 = covers some but misses an important point
0 = misses most important facts

Return ONLY valid JSON in this exact format:

{{
  "correctness": 0,
  "groundedness": 0,
  "completeness": 0,
  "reason": "brief explanation"
}}
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
        "content": judge_prompt
        }
    ],
    max_tokens=256
    )

    return json.loads(response.choices[0].message.content)

# COMMAND ----------

evaluation_results = []

for item in evaluation_set:

    question = item["question"]
    expected_facts = item["expected_facts"]

    answer, context = answer_question(
        question,
        return_context=True
    )

    scores = judge_answer(
        question,
        expected_facts,
        answer,
        context
    )

    evaluation_results.append({
        "question": question,
        "answer": answer,
        "correctness": scores["correctness"],
        "groundedness": scores["groundedness"],
        "completeness": scores["completeness"],
        "reason": scores["reason"]
    })

# COMMAND ----------

import pandas as pd

eval_df = pd.DataFrame(evaluation_results)

display(
    eval_df[
        [
            "question",
            "correctness",
            "groundedness",
            "completeness",
            "reason"
        ]
    ]
)

# COMMAND ----------

# DBTITLE 1,summary
summary = {
    "questions": len(eval_df),
    "correctness_pct": round(eval_df["correctness"].mean() / 2 * 100, 1),
    "groundedness_pct": round(eval_df["groundedness"].mean() / 2 * 100, 1),
    "completeness_pct": round(eval_df["completeness"].mean() / 2 * 100, 1),
}

summary

# COMMAND ----------

# DBTITLE 1,save it

eval_df.to_csv("chess_rag_evaluation_results.csv", index=False)
