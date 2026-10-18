# Databricks notebook source


csv_path = "/Volumes/workspace/chess_rag/source_data/chess_rag_corpus.csv"

df = (
    spark.read
    .option("header", True)
    .option("inferSchema", True)
    .option("multiLine", True)
    .option("quote", '"')
    .option("escape", '"')
    .csv(csv_path)
)

display(df)



# COMMAND ----------

table_name = "workspace.chess_rag.chess_corpus"

spark.sql( f"drop table {table_name}" )



# COMMAND ----------

table_name = "workspace.chess_rag.chess_corpus"

(
    df.write
    .format("delta")
    .mode("overwrite")
    .saveAsTable(table_name)
)


# COMMAND ----------

spark.sql(f"SELECT COUNT(*) FROM {table_name}").show()

# COMMAND ----------

print("Total rows:", df.count())

print("Distinct chunk IDs:", df.select("chunk_id").distinct().count())

print("Rows with null chunk_id:", df.filter("chunk_id IS NULL").count())

# COMMAND ----------

spark.sql(f"""
    SELECT
        COUNT(*) AS row_count,
        COUNT(DISTINCT chunk_id) AS distinct_chunk_ids
    FROM {table_name}
""").show()

# COMMAND ----------

spark.table(table_name).printSchema()

# COMMAND ----------

display(
    spark.sql(f"""
        SELECT
            chunk_id,
            book,
            chapter_title,
            content_type,
            chunk_text
        FROM {table_name}
        ORDER BY chunk_id
        LIMIT 5
    """)
)

# COMMAND ----------

spark.sql("""
ALTER TABLE workspace.chess_rag.chess_corpus
SET TBLPROPERTIES (delta.enableChangeDataFeed = true)
""")

# COMMAND ----------

spark.sql("""
SHOW TBLPROPERTIES workspace.chess_rag.chess_corpus
""").filter("key = 'delta.enableChangeDataFeed'").show(truncate=False)