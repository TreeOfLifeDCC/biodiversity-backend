import os

from elasticsearch import AsyncElasticsearch, AIOHttpConnection
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
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
               phylogeny_filters: str = None):
    print(phylogeny_filters)
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
    response = await es.search(
        index=index, sort=sort, from_=offset, size=limit, body=body
    )
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


from pydantic import BaseModel

class Item(BaseModel):
    taxonomyFilter: list
    filter: str
    downloadOption: str
    taxonId: str



@app.post("/data-download")
async def get_data_files(item: Item):
    data = item
    print(data)
    # test = getDataFiles(search, filter, from_param, size, sort_column, sort_order, taxonomy_filter,download_option)
    # print(test)


import json
from typing import Optional


def getDataFiles(search: str, filter: str, from_param: str, size: str, sortColumn: str, sortOrder: str, taxonomyFilter: str,downloadOption: str):
    return get_organism_filter_query(search, filter, from_param, size, sortColumn, sortOrder, taxonomyFilter)


def get_organism_filter_query(search: Optional[str], filter: Optional[str], from_param: str, size: str,
                              sort_column: Optional[str], sort_order: Optional[str],
                              taxonomy_filter: Optional[str]) -> str:
    taxa_rank_array = [
        "superkingdom", "kingdom", "subkingdom", "superphylum", "phylum", "subphylum", "superclass", "class",
        "subclass",  "infraclass", "cohort", "subcohort", "superorder", "order", "suborder", "infraorder", "parvorder",
        "section", "subsection", "superfamily", "family", "subfamily", "tribe", "subtribe", "genus", "series",
        "subgenus", "species_group", "species_subgroup", "species", "subspecies", "varietas", "forma"]
    sb = []
    sbt = []
    sort = get_sort_query(sort_column, sort_order)
    is_phylogeny_filter = False
    phylogeny_rank = ""
    phylogeny_tax_id = ""
    search_query = []

    if search:
        search_array = search.split(" ")
        search_query = ["*" + temp + "*" for temp in search_array]

    sb.append("{")
    if from_param != "undefined" and size != "undefined":
        sb.append(f"'from': {from_param}, 'size': {size},")

    if sort:
        sb.append(sort)

    sb.append("'query': { 'bool': { 'must': [")

    if search_query:
        sb.append("{'multi_match': {")
        sb.append("'operator': 'AND',")
        sb.append(f"'query': '{' '.join(search_query)}',")
        sb.append("'fields': ['organism.autocomp', 'commonName.autocomp', 'biosamples.autocomp', 'raw_data.autocomp',"
                  "'mapped_reads.autocomp', 'assemblies_status.autocomp', 'annotation_complete.autocomp', "
                  "'annotation_status.autocomp', 'symbionts_records.organism.text.autocomp']")
        sb.append("}},")

    if taxonomy_filter and taxonomy_filter != "undefined":
        taxa_tree = json.loads(taxonomy_filter)
        if taxa_tree:
            for i, taxa in enumerate(taxa_tree):
                rank = taxa.get("rank")
                taxonomy = taxa.get("taxonomy")
                nested_query = (f"{{ 'nested': {{ 'path': 'taxonomies', 'query': {{"
                                f"'nested': {{ 'path': 'taxonomies.{rank}', 'query': {{"
                                f"'bool': {{ 'must': [{{ 'term': {{ 'taxonomies.{rank}.scientificName': '{taxonomy}' }} }} ]"
                                f"}} }} }} }} }} }}")
                sbt.append(nested_query)
                if i < len(taxa_tree) - 1:
                    sbt.append(",")

    if filter and filter != "undefined":
        filter_array = filter.split(",")
        if taxonomy_filter and taxonomy_filter != "undefined" and sbt:
            sb.append("".join(sbt) + ",")

        for filt in filter_array:
            split_array = filt.split("-")
            filter_type = split_array[0].strip()
            filter_value = split_array[1].strip()

            if filter_type == "Biosamples":
                sb.append(f"{{'terms': {{'biosamples': ['{filter_value}']}}}},")
            elif filter_type == "Raw data":
                sb.append(f"{{'terms': {{'raw_data': ['{filter_value}']}}}},")
            elif filter_type == "Mapped reads":
                sb.append(f"{{'terms': {{'mapped_reads': ['{filter_value}']}}}},")
            elif filter_type == "Assemblies":
                sb.append(f"{{'terms': {{'assemblies_status': ['{filter_value}']}}}},")
            elif filter_type == "Annotation complete":
                sb.append(f"{{'terms': {{'annotation_complete': ['{filter_value}']}}}},")
            elif filter_type == "Annotation":
                sb.append(f"{{'terms': {{'annotation_status': ['{filter_value}']}}}},")
            elif filter_type == "Genome Notes":
                sb.append(
                    "{{ 'nested': {{ 'path': 'genome_notes', 'query': {{ 'bool': {{ 'must': [{{'exists': {{ 'field': 'genome_notes.url'}}}} ] }} }} }} }},")
            elif filter_type in taxa_rank_array:  # Assuming taxa_rank_array is predefined
                is_phylogeny_filter = True
                phylogeny_rank = filter_type
                phylogeny_tax_id = filter_value
                sb.append(f"{{ 'nested': {{ 'path': 'taxonomies', 'query': {{ "
                          f"'nested': {{ 'path': 'taxonomies.{phylogeny_rank}', 'query': {{ 'bool': {{ 'must': ["
                          f"{{ 'term': {{ 'taxonomies.{phylogeny_rank}.tax_id': '{phylogeny_tax_id}' }} }} ] }} }} }} }} }} }},")

    sb.append("]}},")

    # Adding aggregations (assumed structure remains the same)
    sb.append("'aggregations': {")
    sb.append("'kingdomRank': { 'nested': { 'path':'taxonomies.kingdom'},")
    sb.append("'aggs':{'scientificName':{'terms':{'field':'taxonomies.kingdom.scientificName', 'size': 20000},")
    sb.append("'aggs':{'commonName':{'terms':{'field':'taxonomies.kingdom.commonName', 'size': 20000}},")
    sb.append("'taxId':{'terms':{'field':'taxonomies.kingdom.tax_id.keyword', 'size': 20000}}}}}},")

    if taxonomy_filter and taxonomy_filter != "undefined" and not is_phylogeny_filter:
        taxa_tree = json.loads(taxonomy_filter)
        if taxa_tree:
            last_taxa = taxa_tree[-1]
            child_rank = last_taxa.get("childRank")
            sb.append(f"'childRank': {{ 'nested': {{ 'path':'taxonomies.{child_rank}' }},")
            sb.append(
                f"'aggs':{{'scientificName':{{'terms':{{'field':'taxonomies.{child_rank}.scientificName', 'size': 20000}}}},")
            sb.append(
                f"'aggs':{{'commonName':{{'terms':{{'field':'taxonomies.{child_rank}.commonName', 'size': 20000}}}},")
            sb.append(f"'taxId':{{'terms':{{'field':'taxonomies.{child_rank}.tax_id.keyword', 'size': 20000}}}}}}}},")
    elif is_phylogeny_filter:
        sb.append(f"'childRank': {{ 'nested': {{ 'path':'taxonomies.{phylogeny_rank}' }},")
        sb.append(
            f"'aggs':{{'scientificName':{{'terms':{{'field':'taxonomies.{phylogeny_rank}.scientificName', 'size': 20000}}}},")
        sb.append(
            f"'aggs':{{'commonName':{{'terms':{{'field':'taxonomies.{phylogeny_rank}.commonName', 'size': 20000}}}},")
        sb.append(f"'taxId':{{'terms':{{'field':'taxonomies.{phylogeny_rank}.tax_id.keyword', 'size': 20000}}}}}}}},")

    # Additional aggregations
    sb.append("'symbionts_biosamples_status': {'terms': {'field': 'symbionts_biosamples_status'}},")
    sb.append("'symbionts_raw_data_status': {'terms': {'field': 'symbionts_raw_data_status'}},")
    sb.append("'symbionts_assemblies_status': {'terms': {'field': 'symbionts_assemblies_status'}},")
    sb.append("'biosamples': {'terms': {'field': 'biosamples'}},")
    sb.append("'raw_data': {'terms': {'field': 'raw_data'}},")
    sb.append("'mapped_reads': {'terms': {'field': 'mapped_reads'}},")
    sb.append("'assemblies': {'terms': {'field': 'assemblies_status'}},")
    sb.append("'annotation_complete': {'terms': {'field': 'annotation_complete'}},")
    sb.append("'annotation': {'terms': {'field': 'annotation_status'}},")
    sb.append("'experiment': { 'nested': { 'path':'experiment'},")
    sb.append("'aggs':{")
    sb.append("'library_construction_protocol':{'terms':{'field':'experiment.library_construction_protocol.keyword'},")
    sb.append("'aggs' : { 'organism_count' : { 'reverse_nested' : {}}")
    sb.append("}}}},")
    sb.append("'genome': { 'nested': { 'path':'genome_notes'},")
    sb.append("'aggs':{")
    sb.append("'genome_count':{'cardinality':{'field':'genome_notes.id'}}")
    sb.append("}}}}")

    sb.append("}}")

    query = "".join(sb).replace("'", '"').replace(",]", "]")
    return query


def get_sort_query(sort_column: Optional[str], sort_order: Optional[str]) -> str:
    # Placeholder function for sort query generation
    if sort_column and sort_order:
        return f"'sort': [{{'{sort_column}': '{sort_order}'}}],"
    return ""
