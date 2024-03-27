import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import warnings

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings("ignore")

from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection



def update_symbionts_status():
    es = Elasticsearch(
        ['es_host'], connection_class=RequestsHttpConnection,
        http_auth=('username', 'password'),
        use_ssl=True, verify_certs=False)

    data = es.search(index='data_portal', size=10000, from_=0, track_total_hits=True)

    for record in data['hits']['hits']:
        recordset = record['_source']

        if "symbionts_records" in recordset and recordset["symbionts_records"]:
            symbionts_biosamples_status = "Submitted to BioSamples"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"symbionts_biosamples_status": symbionts_biosamples_status}})

        if "symbionts_experiments" in recordset and recordset["symbionts_experiments"]:
            symbionts_raw_data_status = "Raw Data Available"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"symbionts_raw_data_status": symbionts_raw_data_status}})

        if "symbionts_assemblies" in recordset and recordset["symbionts_assemblies"]:
            symbionts_assemblies_status = "Assemblies Submitted"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"symbionts_assemblies_status": symbionts_assemblies_status}})



def update_metagenomes_status():
    es = Elasticsearch(
        ['es_host'], connection_class=RequestsHttpConnection,
        http_auth=('username', 'password'),
        use_ssl=True, verify_certs=False)

    data = es.search(index='data_portal', size=10000, from_=0, track_total_hits=True)

    for record in data['hits']['hits']:
        recordset = record['_source']

        if "metagenomes_records" in recordset and recordset["metagenomes_records"]:
            metagenomes_biosamples_status = "Submitted to BioSamples"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"metagenomes_biosamples_status": metagenomes_biosamples_status}})

        if "metagenomes_experiments" in recordset and recordset["metagenomes_experiments"]:
            metagenomes_raw_data_status = "Raw Data Available"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"metagenomes_raw_data_status": metagenomes_raw_data_status}})

        if "metagenomes_assemblies" in recordset and recordset["metagenomes_assemblies"]:
            metagenomes_assemblies_status = "Assemblies Submitted"
            es.update(index='data_portal', id=record['_id'],
                      body={"doc": {"metagenomes_assemblies_status": metagenomes_assemblies_status}})



# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    update_symbionts_status()
    update_metagenomes_status()
