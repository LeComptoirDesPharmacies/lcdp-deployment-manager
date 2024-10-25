from datetime import datetime, timezone, timedelta

import boto3

import logging

cloudwatch_client = boto3.client('cloudwatch')

def __search_expression(env, env_color, metric_name, aggregator):
    return "SEARCH('{{LCDP-SMUGGLER,ServiceEnvironment,ServiceVersion,SmugglerId}} MetricName=\"{metric_name}\" ServiceEnvironment=\"{service_environment}\" ServiceVersion=\"{service_version}\"', '{aggregator}', 30)".format(metric_name=metric_name, service_environment=env, service_version=env_color, aggregator=aggregator)

def __get_smugglers_metric_value(response, metric_name, aggregator):
    values = [x['Values'][0] for x in response['MetricDataResults'] if x['Id'] == metric_name and len(x['Values']) > 0]
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
                "Expression": __search_expression(env, env_color, "ActiveJobs", 'Maximum'),
            },
            {
                'Id': 'pending_jobs',
                "Expression": __search_expression(env, env_color, "PendingJobs", 'Maximum'),
            },
        ],
        StartTime=start_time,
        EndTime=end_time,
        ScanBy='TimestampDescending'
    )

    metrics = dict()

    try:
        active_jobs = __get_smugglers_metric_value(response, 'active_jobs', max)
        if active_jobs is not None:
            metrics['active_jobs'] = active_jobs
    except (Exception):
        logging.exception("An error occured while retrieving 'active_jobs'")

    try:
        pending_jobs = __get_smugglers_metric_value(response, 'pending_jobs', max)
        if pending_jobs is not None:
            metrics['pending_jobs'] = pending_jobs
    except (Exception):
        logging.exception("An error occured while retrieving 'pending_jobs'")

    return metrics
