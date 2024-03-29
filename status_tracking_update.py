
from elasticsearch import Elasticsearch, RequestsHttpConnection

es = Elasticsearch(
    ['https://prj-ext-prod-planet-bio-dr.es.europe-west2.gcp.elastic-cloud.com'],
    http_auth=('elastic', 'VWpqscMp3qPp6Yx8UnAjDdpJ'),
    scheme="https", port=443, )


def get_samples(index_name, es):
    samples = dict()
    data = es.search(index=index_name, size=10000)
    for sample in data['hits']['hits']:
        samples[sample['_id']] = sample['_source']
    return samples


def main():
    x = 1
    data_portal_samples = get_samples('data_portal', es)
    print(len(data_portal_samples))
    for organism, record in data_portal_samples.items():
        tmp = dict()
        tmp['organism'] = record['organism']
        tmp['commonName'] = record['commonName']
        tmp['biosamples'] = 'Done'
        tmp['biosamples_date'] = None
        tmp['ena_date'] = None
        tmp['annotation_date'] = None
        tmp['raw_data'] = check_raw_data_status(record)
        tmp['mapped_reads'] = tmp['raw_data']
        tmp['assemblies_status'] = check_assemblies(record)
        tmp['annotation_status'] = 'Waiting'
        tmp['annotation_complete'] = check_annotation_complete(record)
        tmp['trackingSystem'] = [
            {'name': 'biosamples', 'status': 'Done', 'rank': 1},
            {'name': 'mapped_reads', 'status': tmp['mapped_reads'], 'rank': 2},
            {'name': 'assemblies', 'status': tmp['assemblies_status'], 'rank': 3},
            {'name': 'raw_data', 'status': tmp['raw_data'], 'rank': 4},
            {'name': 'annotation', 'status': 'Waiting', 'rank': 5},
            {'name': 'annotation_complete',
             'status': tmp['annotation_complete'], 'rank': 6}
        ]
        if 'taxonomies' in record:
            tmp['taxonomies'] = record['taxonomies']
        tmp['project_name'] = record['project_name']
        x += 1
        es.index('tracking_status_index', tmp, id=organism)
    print(x)
    return f'Tracking status index updated!'

def check_raw_data_status(record):
    if 'experiment' in record and len(record['experiment']) > 0:
        return 'Done'
    else:
        return 'Waiting'


def check_assemblies(record):
    if 'assemblies' in record and len(record['assemblies']) > 0:
        return 'Done'
    else:
        return 'Waiting'


def check_annotation_complete(record):
    if record['currentStatus'] == 'Annotation Complete':
        return 'Done'
    else:
        return 'Waiting'




if __name__ == '__main__':
    main()