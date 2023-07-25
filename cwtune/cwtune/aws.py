import boto3
import click
from utils import shorten_url

def list_metrics(aws_profile=None, region='us-east-1'):
    """List all CloudWatch metrics."""
    if aws_profile:
        boto3.setup_default_session(
            profile_name=aws_profile, region_name=region)
    client = boto3.client('cloudwatch', region_name=region)

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

def get_metric_data(start, end, metric_name, metric_namespace, dimensions, period, statistic, aws_profile=None, region='us-east-1'):
    """Get metric data from CloudWatch."""
    if aws_profile:
        boto3.setup_default_session(
            profile_name=aws_profile, region_name=region)
    client = boto3.client('cloudwatch', region_name=region)

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

def create_cloudwatch_alarm(name, namespace, dimensions, threshold, alarm_type, aws_profile=None, region='us-east-1', statistic='Sum', period=5, min_duration=3):
    """Create a CloudWatch alarm for the given metric."""

    if aws_profile:
        session = boto3.session.Session(profile_name=aws_profile, region_name=region)
        client = session.client('cloudwatch')
    else:
        client = boto3.client('cloudwatch', region_name=region)

    if alarm_type == 'gt':
        alarm_type = 'GreaterThanThreshold'
    elif alarm_type == 'lt':
        alarm_type = 'LessThanThreshold'

    # suggest actions based on exisitng alarms
    alarms = list_alarms(aws_profile, region)
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
        response = client.put_metric_alarm(
            AlarmName=f"{name} {alarm_type} {threshold}",
            AlarmDescription=f"Created by availabl.ai/cwtune for {name} {alarm_type} {threshold}",
            MetricName=name,
            Namespace=namespace,
            Dimensions=dimensions,
            Statistic=statistic,
            Period=period * 60,
            DatapointsToAlarm=min_duration,
            EvaluationPeriods=min_duration,
            Threshold=threshold,
            ActionsEnabled=True,
            AlarmActions=actions,
            ComparisonOperator=alarm_type,
            TreatMissingData='missing',
            Tags=[
                {
                    'Key': 'cwtune',
                    'Value': 'true'
                },
            ]
        )

        click.echo(f"Successfully created/updated alarm")
        link = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#alarm:alarmFilter=ANY;name={name}%20{alarm_type}%20{threshold}"
        click.echo(f"View alarm: {shorten_url(link)}")

    except Exception as e:
        click.echo(f"Error while creating CloudWatch alarm: {e}")
        return 1

    return 0

def list_alarms(aws_profile=None, region='us-east-1'):
    """List all CloudWatch alarms."""
    if aws_profile:
        boto3.setup_default_session(
            profile_name=aws_profile, region_name=region)
    client = boto3.client('cloudwatch', region_name=region)

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