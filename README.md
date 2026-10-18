
# Chess Mentor – RAG on Databricks

A Retrieval-Augmented Generation (RAG) application built on Databricks that answers chess strategy questions using a small corpus of public-domain chess books.

The project was built as a portfolio demonstration of an end-to-end Generative AI workflow using Databricks components including Delta Lake, AI Search, Unity Catalog, Unity Gateway, and LLM-based evaluation.

## Overview

I have been learning to play chess, and I noticed that there are many models which can play chess extremely well, such as Stockfish. But when you query Stockfish all it will do is tell you the "best move" in the situation, or perhaps the top-three best moves.

What it will not do is explain *why* a particular move is the "best move".  

So the idea was to create a chess application which will not play chess, but rather will explain how to play the game and advise on strategy and tactics.  It will also be able to explain why a particular move is a good move and what the implications of that move are.

The longer-term idea is to create a chess application that can explain why a move is good and what its implications are. For the first phase, I focused on a RAG application that answers general chess strategy questions from instructional source material

So, the first phase was to create a chess based RAG application.  The idea was to download some public domain chess books and create a corpus that could be used to query and thereby explain chess concepts.

I was studying for the *Databricks Generative AI Associate* exam at the time, and so I thought that this would be a good way to explore and practice the concepts in the exam, as well as having some fun and hopefully ending with an application that I could actually use myself.



So, the goal was not to build an engine that plays chess, but to build an AI system that explains chess concepts using public domain source material.



## Architecture

```text
Public-domain chess books
        ↓
HTML parsing and cleaning
        ↓
Paragraph-aware chunking
        ↓
Delta table in Unity Catalog
        ↓
Databricks AI Search
Hybrid retrieval
        ↓
Top-k retrieved chunks
        ↓
Prompt construction
        ↓
Qwen3 via Unity Gateway
        ↓
Grounded answer with citations
        ↓
LLM-as-a-judge evaluation

```

## Source Data

I started the initial corpus with two public-domain chess books:

- *Chess Strategy* – Edward Lasker
- *Chess Fundamentals* – José Raúl Capablanca

As these were both published in 1921 they are in the public domain, and yet hopefully the contents will be essentially timeless.

I downloaded them both from [Project Gutenberg](https://www.gutenberg.org) in html format.


## Data Preparation and Chunking

I found that each book had a different html structure, so each book has its own python parser.

### Challenges with the Chunking process

The first challenge I encountered is that chess books are not easy to read!

Large sections of both books are simply discussions of a chess board and the potential moves.  Capablanca's book was particularly like this.  While this is to be expected in a chess tutorial, what i needed for the rag corpus was information of a more general nature.  

In the end I created a small python proc to classify each paragraph into one of three categories : 

    - position commentary  
    - chess concepts  
    - mixed (paragraphs with both concepts and position commentary)  

I was then able to filter out much of the position commentary as it seemed to me that this was not the sort of material that you could easily query.

Another challenge was the chess notation. Both of these books use the the older descriptive chess notation (K4, Q2, N6, etc), and the notion conventions were slightly different in each book too.  This of course is to be expected when using books over 100 years old.  It would be nice to convert the old notation to the  more modern algebraic notation (A1 to H8 for instance).  That could be an enhancement for the future.

A further challenge was the chess paragraphs themselves.  While I filtered out the chess diagrams, this left many of the paragraphs as incomplete.  I had to explicitly join paragraphs which spanned more than one *p* marker.


I used python's beautifulsoup module to parse each html document and extract the paragraphs used in the chunking.

I kept the chapter headings, and the paragraph type described earlier as metadata for each chunk, as I thought this might be useful later when querying the corpus.

So, each chunk had the following additional attributes :

```text
book
chapter_title
chunk_index
content_type
```

When each book was chunked in a way that seemed ok to me, I then saved each book's chunks to a csv file.

A third python script *build_corpus.py* was used to concantenate the two csv files, and also to add globally unique *chunk_id* column.

The final corpus contained 196 chunks, which I thought was enough for a V1 phase.

## Databricks 

The next step was to upload the corpus in csv format to Databricks.

I used the [Databricks free Community Edition](https://www.databricks.com/learn/free-edition) for this project.

I created a Unity Catalog volume for the csv data, and schema under the *workspace* catalog.

The corpus delta table was stored in : 

```text
workspace.chess_rag.chess_corpus
```

The table columns reflected the additional meta-data associated with each chunk :

```text
chunk_id
book
chapter_title
chunk_index
content_type
chunk_text
```

I also had to enable *Change Data Feed* on the table, as this is a prerequisite for the Delta Sync AI Search index.

## Retrieval and the AI Search Index

It was time to create the *Databricks AI Search index* on the Delta table.

Key Decisions during index creation :

- which index type (Hybrid or Full-Text search)
- which embedding model to use

Hybrid search was chosen because the corpus contains both:

- semantic concepts such as "control of the centre"
- exact chess terminology and historical notation


### Embedding model

There were 3 options presented at the time :
- databricks-gte-large
- databricks-bge-large-en
- databricks-qwen3-embedding-0-6b

The Qwen3 embedding model was selected as it is a strong general-purpose default available in the workspace. Model comparison was out of scope for the initial version, but could be evaluated later using the same retrieval test set.

### Configuration Summary:

```text
Index type: Hybrid
Embedding model: databricks-qwen3-embedding-0-6b
Embedding column: chunk_text
Primary key: chunk_id
Update mode: Triggered
```




## Generation

The next task was to select an LLM to use with the retrieval.

*system.ai.qwen3-next-80b-a3b-instruct* was used for answer generation.  This is one of Databricks Foundation models, as a result you don't have to setup your own AI serving endpoint, which helped to simplify the project considerably.

The LLM was then instructed to answer using only the retrieved source material, and to cite the retrieved passages inline which were used in the generated answer.

For exmple :

```text
[SOURCE 1]
[SOURCE 2]
[SOURCE 3]
```

I then manually tacked on the retrieved chunks to the end of the answer using the retrieval metadata, based on the cited chunks that the LLM had actually used in the answer.

Example:

```text
Control of the centre is important because it supports successful
attacks and helps maintain the initiative [SOURCE 1].

Sources:
- SOURCE 1: Chess Fundamentals, CHAPTER I, chunk 124
```

This provides traceability from the generated answer back to the original corpus.

## Evaluation

The evaluation phase was one of the hardest parts of the project.  

Part of the problem was that I am not a chess expert myself, so I wasn't sure how to write suitable questions or then check the subsequent answers.

In the end I got chatgpt to write a set of 15 chess questions.  More importantly, with each question it included a set of expected facts that were expected to see in the answer.  What this allowed me to do then is use *LLM as a judge* to assess the quality of the responses based on a number of criteria, such as :

- Correctness
- Groundedness
- Completeness

Each criterion was scored from 0 to 2.

Here are the initial results:

```text
Correctness:   96.7%
Groundedness:  100%
Completeness:  80.0%
```

These scores are based on a small LLM-judged evaluation set and should be treated as development metrics rather than formal benchmarks.

## Example Failure Analysis

Evaluation exposed several useful failure modes.

### Correct retrieval, imperfect synthesis

For a question about opposition in pawn endings, the correct source passages were retrieved, but the language model combined two related rules incorrectly.

This demonstrated that strong retrieval does not guarantee a fully correct generated answer.

### Good grounding, incomplete answer

For some questions, the answer remained fully grounded but did not include every expected concept.

This showed the importance of evaluating correctness, grounding, and completeness separately.

## Technologies

- Databricks
- Unity Catalog
- Delta Lake
- Databricks AI Search
- Hybrid vector search
- Databricks Unity Gateway
- Qwen3 embedding model
- Qwen3 instruct model
- Python
- Pandas
- Spark
- LLM-as-a-judge evaluation

## Repository Structure

```text
.
├── data/
├── src/
├── notebooks/
├── evaluation/
└── README.md
```

## Limitations

The current version has several deliberate limitations:

- The corpus is small.
- Historical descriptive chess notation is preserved rather than converted to modern algebraic notation.
- The application explains chess concepts but does not analyse live board positions.
- Evaluation uses an LLM judge and only a small test set.
- Retrieval currently uses a fixed top-k strategy.

## Possible Future Improvements

Potential extensions include:

- add more public-domain chess material
- convert the chess notation to modern algebraic notation
- convert the diagrams in each book to FEN notation. This would mean that some of the position commentary chunks could potentially be used in the corpus.
- convert descriptive notation to algebraic notation
- add reranking
- experiment with retrieval thresholds and chunk sizes
- compare embedding models
- add a lightweight user interface
- integrate Stockfish for position analysis
- evaluate with a larger manually validated test set

## Example Questions


Here are some of the same questions that is used to evaluate the rag application :

- Why is control of the centre important in chess?
- What is the opposition in a pawn ending?
- Why should I avoid moving the same piece several times in the opening?
- Why are two bishops often stronger than two knights?

## Project Goal

The project demonstrates a complete RAG workflow on Databricks:

```text
ingestion
→ chunking
→ Delta storage
→ vector indexing
→ retrieval
→ grounded generation
→ citations
→ evaluation
```

The focus is on building a small but complete system that can be explained, tested, and improved.


