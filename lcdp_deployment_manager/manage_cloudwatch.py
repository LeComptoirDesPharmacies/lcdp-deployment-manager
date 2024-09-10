from datetime import datetime, timezone, timedelta

import boto3

cloudwatch_client = boto3.client('cloudwatch')


def get_smuggler_metrics(namespace_name, metric_name_active_jobs, metric_name_pending_jobs, dimension_name_color,
                       env_color):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=30)

    response = cloudwatch_client.get_metric_data(
        MetricDataQueries=[
            {
                'Id': 'active_jobs',
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace_name,
                        'MetricName': metric_name_active_jobs,
                        'Dimensions': [
                            {
                                'Name': dimension_name_color,
                                'Value': env_color
                            },
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Maximum'
                }
            },
            {
                'Id': 'pending_jobs',
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace_name,
                        'MetricName': metric_name_pending_jobs,
                        'Dimensions': [
                            {
                                'Name': dimension_name_color,
                                'Value': env_color
                            },
                        ]
                    },
                    'Period': 300,
                    'Stat': 'Maximum'
                }
            },
        ],
        StartTime=start_time,
        EndTime=end_time
    )

    try:
        active_jobs = response['MetricDataResults'][0]['Values'][0]
    except (KeyError, IndexError, TypeError):
        active_jobs = 0

    try:
        pending_jobs = response['MetricDataResults'][1]['Values'][0]
    except (KeyError, IndexError, TypeError):
        pending_jobs = 0

    return {
        'active_jobs': active_jobs,
        'pending_jobs': pending_jobs
    }
