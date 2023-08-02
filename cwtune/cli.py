"""Console script for CloudTune."""
import sys
import click
import boto3
from enum import Enum
from .analyze import run

class AlarmType(Enum):
    """An enum for the alarm type."""

    GREATER_THAN = 'gt'
    LESS_THAN = 'lt'

    def values():
        return [a.value for a in AlarmType]

    def from_string(s):
        """Return the AlarmType from the string."""
        if s == 'gt':
            return AlarmType.GREATER_THAN
        elif s == 'lt':
            return AlarmType.LESS_THAN
        else:
            raise ValueError("Invalid AlarmType")

    def to_cw_operator(self):
        """Return the CloudWatch operator for the AlarmType."""
        if self == AlarmType.GREATER_THAN:
            return 'GreaterThanThreshold'
        elif self == AlarmType.LESS_THAN:
            return 'LessThanThreshold'
        else:
            raise ValueError("Invalid AlarmType")
        
    def is_lt(self):
        return self == AlarmType.LESS_THAN
    
    def is_gt(self):
        return self == AlarmType.GREATER_THAN

class AlarmTypeChoice(click.Choice):
    """A custom click.Choice that allows for the user to specify the alarm type as either 'gt' or 'lt'."""

    def __init__(self):
        super().__init__(AlarmType.values())

class AWSRegion(click.Choice):
    """A custom click.Choice that allows for the user to specify the AWS region."""

    def __init__(self):
        super().__init__(boto3.session.Session().get_available_regions('cloudwatch'))

class CLIProfile(click.Choice):

    def __init__(self):
        super().__init__(boto3.session.Session().available_profiles)



@click.command()
@click.option('--alarm-type', prompt='Alarm Type', type=AlarmTypeChoice(), help='The type of alarm, greater than (gt) or less than (lt).')
@click.option('--period', prompt='Period (Mins)', default="5", type=click.Choice(["1", "5", "60"]), help='The period of the CloudWatch metric in minutes.')
@click.option('--statistic', prompt='Statistic', default='Sum', type=click.Choice(['Sum', 'Average', 'SampleCount', 'Min', 'Max', 'p50', 'p95', 'p99']), help='The statistic of the CloudWatch metric.')
@click.option('--region', prompt='Region', type=AWSRegion(), default="us-east-1", help='The region of the CloudWatch metric.')
@click.option('--aws-profile', prompt='AWS CLI Profile', type=CLIProfile(), default="default", help='(Optional) The profile configured in AWS CLI to use for making API calls.')
def main(alarm_type, aws_profile=None, period=5, statistic='Sum', region='us-east-1'):
    run(AlarmType.from_string(alarm_type), aws_profile, int(period), statistic=statistic, region=region)

    return 0


if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
