import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
warnings.filterwarnings("ignore")

from elasticsearch import Elasticsearch
from elasticsearch import RequestsHttpConnection


def update_tracking_status_symbionts():
    es = Elasticsearch(
        ['es_host'], connection_class=RequestsHttpConnection,
        http_auth=('username', 'password'),
        use_ssl=True, verify_certs=False)

    data = es.search(index='data_portal', size=10000, from_=0, track_total_hits=True)

    for record in data['hits']['hits']:
        recordset = record['_source']

        # Update records for symbionts
        if "symbionts_records" in recordset and recordset["symbionts_records"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"symbionts_records": recordset["symbionts_records"]}})

        # Update statuses for symbionts
        if "symbionts_assemblies_status" in recordset and recordset["symbionts_assemblies_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"symbionts_assemblies_status": recordset["symbionts_assemblies_status"]}})

        if "symbionts_biosamples_status" in recordset and recordset["symbionts_biosamples_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"symbionts_biosamples_status": recordset["symbionts_biosamples_status"]}})

        if "symbionts_raw_data_status" in recordset and recordset["symbionts_raw_data_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"symbionts_raw_data_status": recordset["symbionts_raw_data_status"]}})


def update_tracking_status_metagenomes():
    es = Elasticsearch(
        ['es_host'], connection_class=RequestsHttpConnection,
        http_auth=('username', 'password'),
        use_ssl=True, verify_certs=False)

    data = es.search(index='data_portal', size=10000, from_=0, track_total_hits=True)

    for record in data['hits']['hits']:
        recordset = record['_source']

        # Update records for metagenomes
        if "metagenomes_records" in recordset and recordset["metagenomes_records"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"metagenomes_records": recordset["metagenomes_records"]}})


        # Update statuses for symbionts
        if "metagenomes_assemblies_status" in recordset and recordset["metagenomes_assemblies_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"metagenomes_assemblies_status": recordset["metagenomes_assemblies_status"]}})

        if "metagenomes_biosamples_status" in recordset and recordset["metagenomes_biosamples_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"metagenomes_biosamples_status": recordset["metagenomes_biosamples_status"]}})

        if "metagenomes_raw_data_status" in recordset and recordset["metagenomes_raw_data_status"]:
            es.update(index='tracking_status_index', id=record['_id'],
                      body={"doc": {"metagenomes_raw_data_status": recordset["metagenomes_raw_data_status"]}})


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    update_tracking_status_symbionts()
    update_tracking_status_metagenomes()
