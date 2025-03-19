# Databricks notebook source
# MAGIC %pip install langchain mlflow==2.10.1 langchain==0.1.5 databricks-vectorsearch==0.22 databricks-sdk==0.18.0 mlflow[databricks]==2.10.1 langchain.community pillow==9.4.0 

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

import os
from pyspark.sql.functions import substring_index

dir_path = "/Volumes/main/db_demo/article_text/pmc_publications"

file_paths = [file.path for file in dbutils.fs.ls(dir_path)]

df = spark.createDataFrame(file_paths, "string").select(substring_index("value", "/", -1).alias("file_name"))

# COMMAND ----------

import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
import glob
from typing import List
import pandas as pd

volume_path = ""
volume_path = "/Volumes/main/db_demo/article_text/pmc_publications"

def read_files(directory: str) -> List[str]:
    documents = []
    processed_files = spark.sql(f"select distinct file_name from main.db_demo.track_articles").collect()
    processed_files = set(row["file_name"] for row in processed_files)
    new_files = [file for file in os.listdir(volume_path) if file not in processed_files]
    for file_name in new_files:
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'r', encoding='utf-8') as file:
            documents.append(file.read())
    return documents

def chunk_text(documents: List[str], chunk_size = 1000, chunk_overlap: int=200) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for doc in documents:
        chunks.extend(text_splitter.split_text(doc))
    return chunks

def process_articles(volume_path):
    print('Reading all these dang articles...')
    documents = read_files(volume_path)

    print(f"Total articles read: {len(documents)}")
    print("Chunking articles..")
    chunks = chunk_text(documents)

    print(f"Total chunks created: {len(chunks)}")
    return chunks

chunks = process_articles(volume_path)

chunks_df = pd.DataFrame(chunks, columns=["chunk"])

# chunks_df.to_csv("/Workspace/Users/samricketts@kubrickgroup.com/Eisai_poc/chunks.csv", index=False)



# COMMAND ----------

from pyspark.sql.functions import pandas_udf
from pyspark.sql.types import ArrayType, StringType
import pandas as pd

@pandas_udf("array<string>")
def get_chunks(dummy):
    return pd.Series([chunks])

spark.udf.register("get_chunks_udf", get_chunks)

# COMMAND ----------

# MAGIC %sql
# MAGIC insert into main.db_demo.full_txt(text)
# MAGIC select explode(get_chunks_udf('dummy')) as text;
# MAGIC
# MAGIC --see how many rows were inserted

# COMMAND ----------

#update track_articles so we dont have duplicates
df.createOrReplaceTempView("temp_table")

spark.sql("""
    insert into main.db_demo.track_articles
    select * from temp_table
    where not exists (
        select 1 from main.db_demo.track_articles
        where temp_table.file_name = main.db_demo.track_articles.file_name
    )
""")


# end of job
