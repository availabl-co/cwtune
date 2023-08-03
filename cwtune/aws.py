import boto3
import click
import math
from .utils import shorten_url

def cw_client(aws_profile="default", region='us-east-1'):
    """Create a CloudWatch client."""
    if aws_profile:
        boto3.setup_default_session(profile_name=aws_profile, region_name=region)
    
    return boto3.client('cloudwatch', region_name=region)

def list_metrics(client):
    """List all CloudWatch metrics."""

    # page through the results
    metrics = []
    next_token = None

    while True:
        if next_token:
            response = client.list_metrics(NextToken=next_token)
        else:
            response = client.list_metrics()

        metrics += response['Metrics']

        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break

    # sort the metrics by namespace and metric name
    metrics = sorted(metrics, key=lambda x: (x['Namespace'], x['MetricName']))
    return metrics

def get_metric_data(start, end, metric_name, metric_namespace, dimensions, period, statistic, client):
    """Get metric data from CloudWatch."""
    try:
        response = client.get_metric_data(
            MetricDataQueries=[
                {
                    'Id': 'metric_1',
                    'MetricStat': {
                        'Metric': {
                            'Namespace': metric_namespace,
                            'MetricName': metric_name,
                            'Dimensions': dimensions
                        },
                        'Period': period * 60,
                        'Stat': statistic,
                    },
                    'ReturnData': True
                },
            ],
            StartTime=start,
            EndTime=end
        )
    except Exception as e:
        print(f"Error while getting metric data from CloudWatch: {e}")
        return []

    # maps the results to time, value pairs
    results = []
    for i in range(len(response['MetricDataResults'][0]['Timestamps'])):
        results.append((response['MetricDataResults'][0]['Timestamps'][i], response['MetricDataResults'][0]['Values'][i]))

    return results

def create_cloudwatch_alarm(name, namespace, dimensions, threshold, alarm_type, client, statistic='Sum', period=5, window_size=3):
    """Create a CloudWatch alarm for the given metric."""

    # suggest actions based on exisitng alarms
    alarms = list_alarms(client)
    actions = set()

    for alarm in alarms:
        if len(alarm['AlarmActions']) > 0:
            for action in alarm['AlarmActions']:
                actions.add(action)

    if len(actions) > 0:
        click.echo("Select and action for the alarm:")
        for i, action in enumerate(actions):
            click.echo(f"{i+1}. {action}")
        click.echo(f"{len(actions)+1}. Provide SNS Topic ARN")

        click.echo(f"{len(actions)+2}. None of the above")
        action = click.prompt("Action", type=int, default=len(actions)+1)

        if action == len(actions)+1:
            actions= [click.prompt("SNS Topic ARN", type=str)]

        elif action == len(actions)+2:
            actions = []
        else:
            actions = [list(actions)[action-1]]

    try:
        type_str = "Greater Than" if alarm_type.is_gt() else "Less Than"

        response = client.put_metric_alarm(
            AlarmName=f"{name} {type_str} {threshold}",
            AlarmDescription=f"Created by availabl.ai/cwtune for {name} {type_str} {threshold}",
            MetricName=name,
            Namespace=namespace,
            Dimensions=dimensions,
            Statistic=statistic,
            Period=period * 60,
            DatapointsToAlarm=math.ceil(window_size / 2),
            EvaluationPeriods=window_size,
            Threshold=threshold,
            ActionsEnabled=True,
            AlarmActions=actions,
            ComparisonOperator=alarm_type.to_cw_operator(),
            TreatMissingData='missing',
            Tags=[
                {
                    'Key': 'cwtune',
                    'Value': 'true'
                },
            ]
        )

        click.echo(f"Successfully created/updated alarm")

        region = client.meta.region_name
        link = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#alarm:alarmFilter=ANY;name={name}%20{alarm_type}%20{threshold}"
        click.echo(f"View alarm: {shorten_url(link)}")

    except Exception as e:
        click.echo(f"Error while creating CloudWatch alarm: {e}")
        return 1

    return 0

def list_alarms(client):
    """List all CloudWatch alarms."""

    # page through the results
    alarms = []
    next_token = None

    while True:
        if next_token:
            response = client.describe_alarms(NextToken=next_token)
        else:
            response = client.describe_alarms()

        alarms += response['MetricAlarms']

        if 'NextToken' in response:
            next_token = response['NextToken']
        else:
            break

    return alarms