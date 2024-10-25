from datetime import datetime, timezone, timedelta

import boto3

import logging

cloudwatch_client = boto3.client('cloudwatch')

def __search_expression(env, env_color, metric_name, aggregator):
    return "SEARCH('{LCDP-SMUGGLER,LCDPEnvironment,ServiceVersion,SmugglerId} MetricName=\"{}\" LCDPEnvironment=\"{}\" ServiceVersion=\"{}\"', '{}', 30)".format(metric_name, env, env_color, aggregator),

def __get_smugglers_metric_value(response, metric_name, aggregator):
    values = [x["Values"][0] for x in response['MetricDataResults'] if x['Id'] == metric_name and len(x['Values']) > 0]
    if len(values) > 0:
        return aggregator(values)
    return None

def get_smuggler_metrics(env, env_color):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=3)

    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'active_jobs',
                "Expression": __search_expression("ActiveJobs", env, env_color, 'Maximum'),
                #"Expression": "SEARCH('Namespace=\"LCDP-SMUGGLER\" MetricName=\"ActiveJobs\" env=\"{}\" Color=\"{}\"', 'Maximum', 30)".format(env, env_color),
            },
            {
                'Id': 'pending_jobs',
                "Expression": __search_expression("ActiveJobs", env, env_color, 'Maximum'),
               # "Expression": "SEARCH('Namespace=\"LCDP-SMUGGLER\" MetricName=\"PendingJobs\" env=\"{}\" Color=\"{}\"', 'Maximum', 30)".format(
               #     env, env_color),
            },
        ],
        StartTime=start_time,
        EndTime=end_time,
        ScanBy='TimestampDescending'
    )

    metrics = dict()

    #for result in response['MetricDataResults']:
    #    if result['Id'] == 'active_jobs':


    try:
        # ['MetricDataResults'][0] : ActiveJobs
        # ['Values'][0] : Most recent value
        active_jobs = __get_smugglers_metric_value(response, 'active_jobs', max)
        #active_jobs = response['MetricDataResults'][0]['Values'][0]
        if active_jobs:
            metrics['active_jobs'] = active_jobs
    except (Exception):
        logging.exception("An error occured while retrieving 'active_jobs'")

    try:
        # ['MetricDataResults'][1] : PendingJobs
        # ['Values'][0] : Most recent value
        pending_jobs = __get_smugglers_metric_value(response, 'pending_jobs', max)
        #pending_jobs = response['MetricDataResults'][1]['Values'][0]
        if pending_jobs:
            metrics['pending_jobs'] = pending_jobs
    except (Exception):
        logging.exception("An error occured while retrieving 'pending_jobs'")

    return metrics
