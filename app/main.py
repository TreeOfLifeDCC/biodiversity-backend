import os
from elasticsearch import AsyncElasticsearch, AIOHttpConnection
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import csv
import io
import json

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

# es = AsyncElasticsearch(
#     [ES_HOST], connection_class=AIOHttpConnection,
#     http_auth=(ES_USERNAME, ES_PASSWORD),
#     use_ssl=True, verify_certs=False)

es = AsyncElasticsearch(
    ['https://prj-ext-prod-planet-bio-dr.es.europe-west2.gcp.elastic-cloud.com/'], connection_class=AIOHttpConnection,
    http_auth=('elastic', 'GD5tjaI3bTBG3qpmlavpv3Ls'),
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


@app.get("/summary")
async def summary():
    response = await es.search(index="summary")
    data = dict()
    data['results'] = response['hits']['hits']
    return data


@app.get("/{index}")
async def root(index: str, offset: int = 0, limit: int = 15,
               sort: str = "rank:desc", filter: str = None,
               search: str = None, current_class: str = 'kingdom',
               phylogeny_filters: str = None, action: str = None):
    print("Koosum phylogeny", phylogeny_filters)

    print("Koosum filter", filter)

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
                    {"term": {filter_name: filter_value}}
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
        response = await es.search(index=index, sort=sort, from_=offset, body=body, size=50000)
    else:
        response = await es.search(index=index, sort=sort, from_=offset, size=limit, body=body)
    data = dict()
    data['count'] = response['hits']['total']['value']
    data['results'] = response['hits']['hits']
    data['aggregations'] = response['aggregations']
    return data


@app.get("/{index}/{record_id}")
async def details(index: str, record_id: str):
    body = dict()
    if index == 'data_portal':
        body["query"] = {
            "bool": {"filter": [{'term': {'organism': record_id}}]}}
        response = await es.search(index=index, body=body)
    else:
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


@app.post("/data-download")
async def get_data_files(item: QueryParam):
    print(item)
    data = await root(item.index_name, 0, item.pageSize,
                      item.sortValue, item.filterValue,
                      item.searchValue, item.currentClass,
                      item.phylogeny_filters, 'download')
    # Now do something magical with the data
    print(data)
    # return f"Data processed: {data}"

    download_option = "annotation"
    csv_data = create_data_files_csv(data['results'], download_option)

    # Return the byte stream as a downloadable CSV file
    return StreamingResponse(
        csv_data,
        media_type='text/csv',
        headers={"Content-Disposition": "attachment; filename=download.csv"}
    )


def create_data_files_csv(results, download_option):
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

    output.seek(0)
    return io.BytesIO(output.getvalue().encode('utf-8'))
