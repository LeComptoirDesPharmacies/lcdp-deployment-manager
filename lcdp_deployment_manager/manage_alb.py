import boto3
from . import common as common
from . import constant as constant

# Client
elbv2_client = boto3.client('elbv2')


# ~~~~~~~~~~~~~~~~ ALB ~~~~~~~~~~~~~~~~

def get_alb_from_aws(alb_name):
    alb_desc = elbv2_client.describe_load_balancers(
        Names=[alb_name]
    )
    # WARNING: If we got multiple alb
    return alb_desc['LoadBalancers'][0]


def get_alb_target_group_arn(alb_arn, color, tg_type):
    expected = (tg_type.upper(), color.upper())
    target_groups_desc = elbv2_client.describe_target_groups(
        LoadBalancerArn=alb_arn
    )
    for tg in target_groups_desc['TargetGroups']:
        if expected == common.get_type_and_color_for_resource(tg['TargetGroupArn'], elbv2_client):
            return tg['TargetGroupArn']


# ~~~~~~~~~~~~~~~~ Listener ~~~~~~~~~~~~~~~~

def get_current_http_listener(alb_arn):
    elb_desc = elbv2_client.describe_listeners(
        LoadBalancerArn=alb_arn
    )
    return __get_http_listener(elb_desc)


# Récupère la couleur actuellement en production
def get_production_color(listener):
    current_target_group_arn = __get_default_forward_target_group_arn_from_listener(listener)
    return __get_color_from_resource(current_target_group_arn).upper()


def __get_http_listener(listeners):
    # Careful if we got multiple http listener
    for listener in listeners['Listeners']:
        if listener['Port'] == 80 and listener['Protocol'] == 'HTTP':
            return listener


def __get_default_forward_target_group_arn_from_listener(listener):
    # Careful if we got multiple forward target group
    for action in listener['DefaultActions']:
        if action['Type'] == 'forward':
            return action['TargetGroupArn']


def __get_color_from_resource(resource_arn):
    tag_desc = elbv2_client.describe_tags(
        ResourceArns=[resource_arn]
    )
    tags = tag_desc['TagDescriptions'][0]['Tags']
    for tag in tags:
        if tag['Key'] == constant.TARGET_GROUP_COLOR_TAG_NAME:
            return tag['Value']

# ~~~~~~~~~~~~~~~~ Rules ~~~~~~~~~~~~~~~~


# Récupère les règles qui n'ont pas une couleur dans l'url de redirection
# ex : blue.beta.verde -> NON ; beta.verde -> OUI
def get_uncolored_rules(listener):
    rules_desc = elbv2_client.describe_rules(
        ListenerArn=listener['ListenerArn']
    )
    uncolored_rules = []
    for rule in rules_desc['Rules']:
        for condition in rule['Conditions']:
            host = condition['HostHeaderConfig']
            if all(__is_uncolored_host_header_value(v) for v in host['Values']):
                uncolored_rules.append(rule)
    return uncolored_rules


def __is_uncolored_host_header_value(value):
    return constant.BLUE not in value.upper() and constant.GREEN not in value.upper()

