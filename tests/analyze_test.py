from cwtune.analyze import run
from cwtune.cli import AlarmType
from datetime import datetime, timezone, timedelta
from unittest import mock

import unittest
class AnalyzeTest(unittest.TestCase):

    CWDATA = {
            'MetricDataResults': [
                {
                    'Timestamps': [
                        datetime(2020, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 1, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 2, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 3, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 4, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 5, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 6, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 7, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 8, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 9, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 10, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 11, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 12, 0, tzinfo=timezone.utc),
                        datetime(2020, 1, 1, 0, 13, 0, tzinfo=timezone.utc)
                    ],
                    'Values': [
                        80,
                        80,
                        80,
                        80,
                        80,
                        100,
                        100,
                        100,
                        100,
                        100,
                        80,
                        80,
                        80,
                        80
                    ]
                }
            ]
        }
    
    @mock.patch('click.prompt', side_effect=['CPUUtilization', 1, 2, 5, 2])
    @mock.patch('click.confirm', side_effect=['Y'])
    def test_end_to_end(self, input, confirm):

        mock_client = mock.Mock()
        mock_client.list_metrics.return_value = {
            'Metrics': [
                {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'CPUUtilization',
                    'Dimensions': [
                        {
                            'Name': 'InstanceId',
                            'Value': 'i-1234567890abcdef0'
                        },
                    ]
                },
                {
                    'Namespace': 'AWS/EC2',
                    'MetricName': 'NetworkIn',
                    'Dimensions': [
                        {
                            'Name': 'InstanceId',
                            'Value': 'i-1234567890abcdef0'
                        },
                    ]
                },
            ]
        }

        mock_client.get_metric_data.return_value = self.CWDATA
        mock_client.describe_alarms.return_value = {
            'MetricAlarms': []
        }
        mock_client.meta.region_name = 'us-east-1'
        mock_client.put_metric_alarm.return_value = {}

        run(AlarmType.GREATER_THAN, 'default', 1, statistic='p99', region='us-east-1', client=mock_client)

        assert mock_client.list_metrics.call_count == 1
        assert mock_client.get_metric_data.call_count == 1
        assert mock_client.describe_alarms.call_count == 1
        assert mock_client.put_metric_alarm.call_count == 1

        # assert correct alarm was created
        args, kwargs = mock_client.put_metric_alarm.call_args
        assert kwargs['AlarmName'] == 'CPUUtilization Greater Than 90'
        assert kwargs['AlarmDescription'] == 'Created by availabl.ai/cwtune for CPUUtilization Greater Than 90'
        assert kwargs['MetricName'] == 'CPUUtilization'
        assert kwargs['Namespace'] == 'AWS/EC2'
        assert kwargs['Dimensions'] == [{'Name': 'InstanceId', 'Value': 'i-1234567890abcdef0'}]
        assert kwargs['Statistic'] == 'p99'
        assert kwargs['Period'] == 60
        assert kwargs['DatapointsToAlarm'] == 3
        assert kwargs['EvaluationPeriods'] == 5
        assert kwargs['Threshold'] == 90

        # assert that the correct metric was passed to get_metric_data
        args, kwargs = mock_client.get_metric_data.call_args
        assert kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['MetricName'] == 'CPUUtilization'
        assert kwargs['MetricDataQueries'][0]['MetricStat']['Metric']['Namespace'] == 'AWS/EC2'