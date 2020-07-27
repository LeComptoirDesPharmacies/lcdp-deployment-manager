import boto3
from . import constant as constant

ses_client = boto3.client('ses', region_name='eu-central-1')


def send_mail_to_developers(message_content):
    ses_client.send_email(
        Source=constant.FROM_MAIL,
        Destination=__build_destination(),
        Message=__build_message_from_content(message_content)
    )


def __build_message_from_content(content):
    return {
        'Body': {
            'Text': {
                'Charset': constant.DEFAULT_CHARSET,
                'Data': content,
            },
        },
        'Subject': {
            'Charset': constant.DEFAULT_CHARSET,
            'Data': '⚠️ ERROR ON DEPLOYMENT SCRIPT ⚠️',
        },
    }


def __build_destination():
    return {
        'ToAddresses': [
            constant.DEVELOPERS_MAIL,
        ],
    }
