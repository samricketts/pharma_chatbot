# Databricks notebook source
# MAGIC %pip install awscli

# COMMAND ----------

dbutils.library.restartPython()

# COMMAND ----------

from pyspark.sql import SparkSession
import os
import subprocess

spark = SparkSession.builder.appName("PMCdownload").getOrCreate()

pmc_file_path = "file:/Workspace/Users/samricketts@kubrickgroup.com/Eisai_poc/pmc_result.txt"
# pmc_file_path = "file:/Workspace/Users/samricketts@kubrickgroup.com/Eisai_poc/pmc_tst.txt"

pmcids_df = spark.read.text(pmc_file_path).withColumnRenamed("value", "pmcid")

pmcids_rdd = pmcids_df.rdd.map(lambda row: row["pmcid"])

local_dir = "/Workspace/Users/samricketts@kubrickgroup.com/Eisai_poc/pmc_publications"
# use volume path instead of workspace

os.makedirs(local_dir, exist_ok = True)

def download_pmcid(pmcid):
    try:
        command = f"aws s3 cp s3://pmc-oa-opendata/author_manuscript/txt/all/{pmcid}.txt {local_dir} --no-sign-request"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return f"Downloaded: {pmcid}.txt"
        else:
            return f"Failed to download {pmcid}.txt. Error: {result.stderr.strip()}"
    except Exception as e:
        return f"Error with {pmcid}: {str(e)}"

# Parallel processing with Spark
def download_partition(iterator):
    import os
    os.makedirs(local_dir, exist_ok=True)  # Ensure directory exists for each worker
    results = [download_pmcid(pmcid) for pmcid in iterator]
    return results

# Execute downloads in parallel
results = pmcids_rdd.mapPartitions(download_partition).collect()

# Print results
for result in results:
    print(result)

# COMMAND ----------

pmcids_df.show()

# COMMAND ----------

!cp -r  /Workspace/Users/samricketts@kubrickgroup.com/Eisai_poc/pmc_publications /Volumes/main/db_demo/article_text/ 

# moving data from workspace to volume

