import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from cwtune.cwtune.cwtune import shorten_url, zero_pad, eval, get_breaches, create_cloudwatch_link, longest_breach, format_timestamp, select_range


class TestCloudTune(unittest.TestCase):

    def test_shorten_url(self):
        with patch('requests.get') as mocked_get:
            mocked_get.return_value.text = 'http://tinyurl.com/test'
            url = 'http://example.com'
            result = shorten_url(url)
            self.assertEqual(result, 'http://tinyurl.com/test')

    def test_zero_pad(self):
        data = []
        period = 1
        start = datetime.utcnow()
        end = datetime.utcnow() + timedelta(minutes=5)

        # round to nearest minute
        start = start.replace(second=0, microsecond=0)
        end = end.replace(second=0, microsecond=0)

        # set tzinfo to UTC
        start = start.replace(tzinfo=timezone.utc)
        end = end.replace(tzinfo=timezone.utc)

        result = zero_pad(data, period, start, end)
        self.assertEqual(len(result), 6)  # should be 6 minutes of data

    def test_eval_gt(self):
        self.assertTrue(eval(2, 1, 'gt'))

    def test_eval_lt(self):
        self.assertTrue(eval(1, 2, 'lt'))

    def test_get_breaches(self):
        data = [(datetime.utcnow(), 1),
                (datetime.utcnow() + timedelta(minutes=5), 2)]
        threshold = 1.5
        alarm_type = 'gt'
        result = get_breaches(data, threshold, alarm_type)
        self.assertEqual(len(result), 1)  # should be 1 breach

    def test_create_cloudwatch_link(self):
        namespace = 'AWS/EC2'
        metric_name = 'CPUUtilization'
        start = datetime(2023, 7, 17, 13, 20, 58)
        end = datetime(2023, 7, 17, 14, 25, 58)
        dimensions = [{'Name': 'InstanceId', 'Value': 'i-0abcd1234efgh5678'}]
        threshold = 80.0
        region = 'us-west-2'
        statistic = 'Average'
        period = 5
        result = create_cloudwatch_link(
            namespace, metric_name, start, end, dimensions, threshold, region, statistic, period, shorten=False)
        self.assertEqual(result, "https://us-west-2.console.aws.amazon.com/cloudwatch/home?region=us-west-2#metricsV2?graph=~(view~'timeSeries~stacked~false~metrics~(~(~'AWS*2fEC2~'CPUUtilization~'InstanceId~'i-0abcd1234efgh5678))~region~'us-west-2~start~'2023-07-17T12:15:58Z~end~'2023-07-17T15:30:58Z~annotations~(horizontal~(~(label~'Threshold~value~80.0))~vertical~(~(label~'Start~value~'2023-07-17T13:20:58Z)~(label~'End~value~'2023-07-17T14:25:58Z)))~stat~'Average~period~300)&query=~'*7bAWS*2fEC2*2c'InstanceId'*7d")

    def test_longest_breach(self):

        now = datetime.utcnow()
        now = now.replace(tzinfo=timezone.utc)

        breaches = [
            {'start': now, 'end': now + timedelta(minutes=5)},
            {'start': now, 'end': now + timedelta(minutes=10)}
        ]
        result = longest_breach(breaches)
        # longest breach is 10 minutes
        self.assertEqual(result, timedelta(minutes=10))

    def test_format_timestamp(self):
        timestamp = datetime(2023, 1, 1, 0, 0, 0)
        result = format_timestamp(timestamp)
        self.assertEqual(result, '2023-01-01 00:00:00')

    def test_select_range(self):
        start, end = select_range()
        # tzinfo should be UTC
        self.assertEqual(start.tzinfo, timezone.utc)
        self.assertEqual(end.tzinfo, timezone.utc)

        # start should be 14 days ago
        now = datetime.utcnow()
        now = now.replace(tzinfo=timezone.utc)

        self.assertTrue((now - start) > timedelta(days=13))
        self.assertTrue((now - end) < timedelta(minutes=1))

if __name__ == '__main__':
    unittest.main()
