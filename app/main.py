import os
from elasticsearch import AsyncElasticsearch, AIOHttpConnection
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import csv
import io
import json
import re

from .constants import DATA_PORTAL_AGGREGATIONS

app = FastAPI()

origins = [
    "*"
]

ES_HOST = os.getenv('ES_CONNECTION_URL')

ES_USERNAME = os.getenv('ES_USERNAME')

ES_PASSWORD = os.getenv('ES_PASSWORD')

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

es = AsyncElasticsearch(
    [ES_HOST],
    timeout=60,
    connection_class=AIOHttpConnection,
    http_auth=(ES_USERNAME, ES_PASSWORD),
    use_ssl=True, verify_certs=False)


@app.get("/gis_filter")
async def get_gis_data(filter: str = None,
                       search: str = None, current_class: str = 'kingdom',
                       phylogeny_filters: str = None):
    print(phylogeny_filters)
    # data structure for ES query
    body = dict()
    # building aggregations for every request
    body["aggs"] = dict()
    for aggregation_field in DATA_PORTAL_AGGREGATIONS:
        body["aggs"][aggregation_field] = {
            "terms": {"field": aggregation_field + ".keyword", "size": 50}
        }
    body["aggs"]["taxonomies"] = {
        "nested": {"path": f"taxonomies.{current_class}"},
        "aggs": {current_class: {
            "terms": {
                "field": f"taxonomies.{current_class}.scientificName"
            }
        }
        }
    }

    if phylogeny_filters:
        body["query"] = {
            "bool": {
                "filter": list()
            }
        }
        phylogeny_filters = phylogeny_filters.split("-")
        print(phylogeny_filters)
        for phylogeny_filter in phylogeny_filters:
            name, value = phylogeny_filter.split(":")
            nested_dict = {
                "nested": {
                    "path": f"taxonomies.{name}",
                    "query": {
                        "bool": {
                            "filter": list()
                        }
                    }
                }
            }
            nested_dict["nested"]["query"]["bool"]["filter"].append(
                {
                    "term": {
                        f"taxonomies.{name}.scientificName": value
                    }
                }
            )
            body["query"]["bool"]["filter"].append(nested_dict)
    # adding filters, format: filter_name1:filter_value1, etc...
    if filter:
        filters = filter.split(",")
        if 'query' not in body:
            body["query"] = {
                "bool": {
                    "filter": list()
                }
            }
        for filter_item in filters:
            if current_class in filter_item:
                _, value = filter_item.split(":")
                nested_dict = {
                    "nested": {
                        "path": f"taxonomies.{current_class}",
                        "query": {
                            "bool": {
                                "filter": list()
                            }
                        }
                    }
                }
                nested_dict["nested"]["query"]["bool"]["filter"].append(
                    {
                        "term": {
                            f"taxonomies.{current_class}.scientificName": value
                        }
                    }
                )
                body["query"]["bool"]["filter"].append(nested_dict)
            else:
                filter_name, filter_value = filter_item.split(":")
                body["query"]["bool"]["filter"].append(
                    {"term": {filter_name + '.keyword': filter_value}}
                )

    # adding search string
    if search:
        # body already has filter parameters
        if "query" in body:
            # body["query"]["bool"].update({"should": []})
            body["query"]["bool"].update({"must": {}})
        else:
            # body["query"] = {"bool": {"should": []}}
            body["query"] = {"bool": {"must": {}}}
        body["query"]["bool"]["must"] = {"bool": {"should": []}}
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"organism.keyword": {"value": f"*{search}*",
                                               "case_insensitive": True}}}
        )
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"commonName.keyword": {"value": f"*{search}*",
                                                 "case_insensitive": True}}}
        )
    print(json.dumps(body))
    response = await es.search(
        index='gis_filter_index', body=body, size=100000,
    )
    data = dict()
    data['count'] = response['hits']['total']['value']
    data['results'] = response['hits']['hits']
    data['aggregations'] = response['aggregations']
    return data


@app.get("/articles")
async def articles(offset: int = 0, limit: int = 15,
                   articleType: str = None,
                   journalTitle: str = None, pubYear: str = None):
    body = dict()
    data_index = 'articles'
    # Aggregations
    body["aggs"] = dict()
    body["aggs"]['journalTitle'] = {
        "terms": {"field": "journalTitle"}
    }
    body["aggs"]['pubYear'] = {
        "terms": {"field": "pubYear"}
    }
    body["aggs"]["articleType"] = {
        "terms": {"field": "articleType"}
    }

    # Filters
    if articleType or journalTitle or pubYear:
        body["query"] = {
            "bool": {
                "filter": list()
            }
        }
    if articleType:
        body["query"]["bool"]["filter"].append(
            {"term": {'articleType': articleType}})
    if journalTitle:
        body["query"]["bool"]["filter"].append(
            {"term": {'journalTitle': journalTitle}})
    if pubYear:
        body["query"]["bool"]["filter"].append({"term": {'pubYear': pubYear}})
    print(body)
    response = await es.search(index=data_index, from_=offset, size=limit,
                               body=body)
    data = dict()
    data['count'] = response['hits']['total']['value']
    data['results'] = response['hits']['hits']
    data['aggregations'] = response['aggregations']
    return data


@app.get("/{index}")
async def root(index: str, offset: int = 0, limit: int = 15,
               sort: str = "rank:desc", filter: str = None,
               search: str = None, current_class: str = 'kingdom',
               phylogeny_filters: str = None, action: str = None):
    # data structure for ES query
    body = dict()
    # building aggregations for every request
    body["aggs"] = dict()
    for aggregation_field in DATA_PORTAL_AGGREGATIONS:
        body["aggs"][aggregation_field] = {
            "terms": {"field": aggregation_field, "size": 50}
        }
    body["aggs"]["taxonomies"] = {
        "nested": {"path": f"taxonomies.{current_class}"},
        "aggs": {current_class: {
            "terms": {
                "field": f"taxonomies.{current_class}.scientificName"
            }
        }
        }
    }
    body["aggs"]["experiment"] = {
        "nested": {"path": "experiment"},
        "aggs": {"library_construction_protocol": {"terms": {
            "field": "experiment.library_construction_protocol.keyword"}
        }
        }
    }
    body["aggs"]["genome"] = {
        "nested": {"path": "genome_notes"},
        "aggs": {"genome_count": {"cardinality": {"field": "genome_notes.id"}
                                  }
                 }
    }
    if phylogeny_filters:
        body["query"] = {
            "bool": {
                "filter": list()
            }
        }
        phylogeny_filters = phylogeny_filters.split("-")
        print(phylogeny_filters)
        for phylogeny_filter in phylogeny_filters:
            name, value = phylogeny_filter.split(":")
            nested_dict = {
                "nested": {
                    "path": f"taxonomies.{name}",
                    "query": {
                        "bool": {
                            "filter": list()
                        }
                    }
                }
            }
            nested_dict["nested"]["query"]["bool"]["filter"].append(
                {
                    "term": {
                        f"taxonomies.{name}.scientificName": value
                    }
                }
            )
            body["query"]["bool"]["filter"].append(nested_dict)
    # adding filters, format: filter_name1:filter_value1, etc...
    if filter:
        filters = filter.split(",")
        if 'query' not in body:
            body["query"] = {
                "bool": {
                    "filter": list()
                }
            }
        for filter_item in filters:
            if current_class in filter_item:
                _, value = filter_item.split(":")
                nested_dict = {
                    "nested": {
                        "path": f"taxonomies.{current_class}",
                        "query": {
                            "bool": {
                                "filter": list()
                            }
                        }
                    }
                }
                nested_dict["nested"]["query"]["bool"]["filter"].append(
                    {
                        "term": {
                            f"taxonomies.{current_class}.scientificName": value
                        }
                    }
                )
                body["query"]["bool"]["filter"].append(nested_dict)

            else:
                filter_name, filter_value = filter_item.split(":")
                if filter_name == 'experimentType':
                    nested_dict = {
                        "nested": {
                            "path": "experiment",
                            "query": {
                                "bool": {
                                    "filter": {
                                        "term": {
                                            "experiment"
                                            ".library_construction_protocol"
                                            ".keyword": filter_value
                                        }
                                    }
                                }
                            }
                        }
                    }
                    body["query"]["bool"]["filter"].append(nested_dict)
                elif filter_name == 'genome_notes':
                    nested_dict = {
                        'nested': {'path': 'genome_notes', 'query': {
                            'bool': {
                                'must': [
                                    {'exists': {
                                        'field': 'genome_notes.url'}}]}}}}
                    body["query"]["bool"]["filter"].append(nested_dict)
                else:
                    print(filter_name)
                    body["query"]["bool"]["filter"].append(
                        {"term": {filter_name: filter_value}})

    # adding search string
    if search:
        # body already has filter parameters
        if "query" in body:
            # body["query"]["bool"].update({"should": []})
            body["query"]["bool"].update({"must": {}})
        else:
            # body["query"] = {"bool": {"should": []}}
            body["query"] = {"bool": {"must": {}}}
        body["query"]["bool"]["must"] = {"bool": {"should": []}}
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"organism": {"value": f"*{search}*",
                                       "case_insensitive": True}}}
        )
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"commonName": {"value": f"*{search}*",
                                         "case_insensitive": True}}}
        )
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"symbionts_records.organism.text": {"value": f"*{search}*",
                                                              "case_insensitive": True}}}
        )
        body["query"]["bool"]["must"]["bool"]["should"].append(
            {"wildcard": {"metagenomes_records.organism.text": {"value": f"*{search}*",
                                                                "case_insensitive": True}}}
        )
    print(json.dumps(body))

    if action == 'download':
        response = await es.search(index=index, sort=sort, from_=offset, body=body, size=10000)
    else:
        response = await es.search(index=index, sort=sort, from_=offset, size=limit, body=body)
    data = dict()
    data['count'] = response['hits']['total']['value']
    data['results'] = response['hits']['hits']
    data['aggregations'] = response['aggregations']
    return data


@app.get("/{index}/{record_id}")
async def details(index: str, record_id: str):
    response = await es.search(index=index, q=f"_id:{record_id}")
    data = dict()
    data['count'] = response['hits']['total']['value']
    data['results'] = response['hits']['hits']
    return data


class QueryParam(BaseModel):
    pageIndex: int
    pageSize: int
    searchValue: str = ''
    sortValue: str
    filterValue: str
    currentClass: str
    phylogeny_filters: str
    index_name: str
    downloadOption: str


@app.post("/data-download")
async def get_data_files(item: QueryParam):
    data = await root(item.index_name, 0, item.pageSize,
                      item.sortValue, item.filterValue,
                      item.searchValue, item.currentClass,
                      item.phylogeny_filters, 'download')

    csv_data = create_data_files_csv(data['results'], item.downloadOption, item.index_name)

    # Return the byte stream as a downloadable CSV file
    return StreamingResponse(
        csv_data,
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=download.csv"}
    )


def create_data_files_csv(results, download_option, index_name):
    header = []
    if download_option.lower() == "assemblies":
        header = ["Scientific Name", "Accession", "Version", "Assembly Name", "Assembly Description",
                  "Link to chromosomes, contigs and scaffolds all in one"]
    elif download_option.lower() == "annotation":
        header = ["Annotation GTF", "Annotation GFF3", "Proteins Fasta", "Transcripts Fasta",
                  "Softmasked genomes Fasta"]
    elif download_option.lower() == "raw_files":
        header = ["Study Accession", "Sample Accession", "Experiment Accession", "Run Accession", "Tax Id",
                  "Scientific Name", "FASTQ FTP", "Submitted FTP", "SRA FTP", "Library Construction Protocol"]
    elif download_option.lower() == "metadata" and 'data_portal' in index_name:
        header = ['Organism', 'Common Name', 'Common Name Source', 'Current Status']
    elif download_option.lower() == "metadata" and 'tracking_status' in index_name:
        header = ['Organism', 'Common Name', 'Metadata submitted to BioSamples', 'Raw data submitted to ENA',
                  'Mapped reads submitted to ENA', 'Assemblies submitted to ENA',
                  'Annotation complete', 'Annotation submitted to ENA']


    output = io.StringIO()
    csv_writer = csv.writer(output)
    csv_writer.writerow(header)

    for entry in results:
        record = entry["_source"]
        if download_option.lower() == "assemblies":
            assemblies = record.get("assemblies", [])
            scientific_name = record.get("organism", "")
            for assembly in assemblies:
                accession = assembly.get("accession", "-")
                version = assembly.get("version", "-")
                assembly_name = assembly.get("assembly_name", "")
                assembly_description = assembly.get("description", "")
                link = f"https://www.ebi.ac.uk/ena/browser/api/fasta/{accession}?download=true&gzip=true" if accession else ""
                entry = [scientific_name, accession, version, assembly_name, assembly_description, link]
                csv_writer.writerow(entry)

        elif download_option.lower() == "annotation":
            annotations = record.get("annotation", [])
            for annotation in annotations:
                gtf = annotation.get("annotation", {}).get("GTF", "-")
                gff3 = annotation.get("annotation", {}).get("GFF3", "-")
                proteins_fasta = annotation.get("proteins", {}).get("FASTA", "")
                transcripts_fasta = annotation.get("transcripts", {}).get("FASTA", "")
                softmasked_genomes_fasta = annotation.get("softmasked_genome", {}).get("FASTA", "")
                entry = [gtf, gff3, proteins_fasta, transcripts_fasta, softmasked_genomes_fasta]
                csv_writer.writerow(entry)

        elif download_option.lower() == "raw_files":
            experiments = record.get("experiment", [])
            for experiment in experiments:
                study_accession = experiment.get("study_accession", "")
                sample_accession = experiment.get("sample_accession", "")
                experiment_accession = experiment.get("experiment_accession", "")
                run_accession = experiment.get("run_accession", "")
                tax_id = experiment.get("tax_id", "")
                scientific_name = experiment.get("scientific_name", "")
                submitted_ftp = experiment.get("submitted_ftp", "")
                sra_ftp = experiment.get("sra-ftp", "")
                library_construction_protocol = experiment.get("library_construction_protocol", "")
                fastq_ftp = experiment.get("fastq_ftp", "")

                if fastq_ftp:
                    fastq_list = fastq_ftp.split(";")
                    for fastq in fastq_list:
                        entry = [study_accession, sample_accession, experiment_accession, run_accession, tax_id,
                                 scientific_name, fastq, submitted_ftp, sra_ftp, library_construction_protocol]
                        csv_writer.writerow(entry)
                else:
                    entry = [study_accession, sample_accession, experiment_accession, run_accession, tax_id,
                             scientific_name, fastq_ftp, submitted_ftp, sra_ftp, library_construction_protocol]
                    csv_writer.writerow(entry)

        elif download_option.lower() == "metadata" and 'data_portal' in index_name:
            organism = record.get('organism', '')
            common_name = record.get('commonName', '')
            common_name_source = record.get('commonNameSource', '')
            current_status = record.get('currentStatus', '')
            entry = [organism, common_name, common_name_source, current_status]
            csv_writer.writerow(entry)

        elif download_option.lower() == "metadata" and 'tracking_status' in index_name:
            organism = record.get('organism', '')
            common_name = record.get('commonName', '')
            metadata_biosamples = record.get('biosamples', '')
            raw_data_ena = record.get('raw_data', '')
            mapped_reads_ena = record.get('mapped_reads', '')
            assemblies_ena = record.get('assemblies_status', '')
            annotation_complete = record.get('annotation_complete', '')
            annotation_submitted_ena = record.get('annotation_status', '')
            entry = [organism, common_name, metadata_biosamples, raw_data_ena, mapped_reads_ena, assemblies_ena,
                     annotation_complete, annotation_submitted_ena]
            csv_writer.writerow(entry)

    output.seek(0)
    return io.BytesIO(output.getvalue().encode('utf-8'))

