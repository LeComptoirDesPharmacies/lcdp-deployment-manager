from datetime import datetime, timezone, timedelta

import boto3

import logging

cloudwatch_client = boto3.client('cloudwatch')


def get_smuggler_metrics(env, env_color):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=3)

    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'active_jobs',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'lcdp-smuggler',
                        'MetricName': 'ActiveJobs',
                        'Dimensions': [
                            {
                                'Name': 'Color',
                                'Value': env_color
                            },
                            {
                                'Name': 'env',
                                'Value': env
                            }
                        ]
                    },
                    'Period': 30,
                    'Stat': 'Maximum'
                }
            },
            {
                'Id': 'pending_jobs',
                'MetricStat': {
                    'Metric': {
                        'Namespace': 'lcdp-smuggler',
                        'MetricName': 'PendingJobs',
                        'Dimensions': [
                            {
                                'Name': 'Color',
                                'Value': env_color
                            },
                            {
                                'Name': 'env',
                                'Value': env
                            }
                        ]
                    },
                    'Period': 30,
                    'Stat': 'Maximum'
                }
            },
        ],
        StartTime=start_time,
        EndTime=end_time,
        ScanBy='TimestampDescending'
    )

    metrics = dict()

    logging.info("response")
    logging.info(response)
    try:
        # ['MetricDataResults'][0] : ActiveJobs
        # ['Values'][0] : Most recent value
        active_jobs = response['MetricDataResults'][0]['Values'][0]
        metrics['active_jobs'] = active_jobs
    except (KeyError, IndexError, TypeError):
        logging.exception("An error occured while retrieving 'active_jobs'")

    try:
        # ['MetricDataResults'][1] : PendingJobs
        # ['Values'][0] : Most recent value
        pending_jobs = response['MetricDataResults'][1]['Values'][0]
        metrics['pending_jobs'] = pending_jobs
    except (KeyError, IndexError, TypeError):
        logging.exception("An error occured while retrieving 'pending_jobs'")

    return metrics
