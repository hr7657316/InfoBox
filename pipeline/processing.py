import os
from dotenv import load_dotenv
from unstructured_ingest.pipeline.pipeline import Pipeline
from unstructured_ingest.interfaces import ProcessorConfig
from unstructured_ingest.processes.connectors.local import (
    LocalIndexerConfig, LocalDownloaderConfig, 
    LocalConnectionConfig, LocalUploaderConfig
)
from unstructured_ingest.processes.partitioner import PartitionerConfig

# Load environment variables from .env file
load_dotenv()

if __name__ == '__main__':
    Pipeline.from_configs(
        context=ProcessorConfig(disable_parallelism=True),
        indexer_config=LocalIndexerConfig(input_path="documents-testing"),
        downloader_config=LocalDownloaderConfig(),
        source_connection_config=LocalConnectionConfig(),
        partitioner_config=PartitionerConfig(
            partition_by_api=True,
            api_key=os.getenv("UNSTRUCTURED_API_KEY"),
            partition_endpoint="https://api.unstructuredapp.io/general/v0/general",
            strategy="auto"
        ),
        uploader_config=LocalUploaderConfig(output_dir="output_documenty")
    ).run()