import boto3
import logging
from . import common as common
from . import constant as constant

# Client
elbv2_client = boto3.client('elbv2')


# ~~~~~~~~~~~~~~~~ ALB ~~~~~~~~~~~~~~~~

def get_alb_from_aws(alb_name):
    """
    Récupère l'application load balancer sur aws
    :param alb_name:    Nom du load balance
    :type alb_name:     str
    :return:            Load balancer trouvé
    :rtype:             dict
    """
    alb_desc = elbv2_client.describe_load_balancers(
        Names=[alb_name]
    )
    # WARNING: If we got multiple alb
    return alb_desc['LoadBalancers'][0]


def get_alb_target_group_arn(alb_arn, color, tg_type):
    """
    Récupère un target group ayant un type et une couleur précise
    :param alb_arn: Arn aws de l'Application load balancer cible
    :type alb_arn:  str
    :param color:   Couleur recherché
    :type color:    str
    :param tg_type: Type recherché
    :type tg_type:  str
    :return:        Target group trouvé
    :rtype:         dict
    """
    expected = (tg_type.upper(), color.upper())
    target_groups_desc = elbv2_client.describe_target_groups(
        LoadBalancerArn=alb_arn
    )
    for tg in target_groups_desc['TargetGroups']:
        if expected == common.get_type_and_color_for_resource(tg['TargetGroupArn'], elbv2_client):
            return tg['TargetGroupArn']


# ~~~~~~~~~~~~~~~~ Listener ~~~~~~~~~~~~~~~~

def get_current_listener(alb_arn, ssl_enabled):
    elb_desc = elbv2_client.describe_listeners(
        LoadBalancerArn=alb_arn
    )
    return __get_listener(elb_desc, ssl_enabled)


def get_production_color(listener):
    """
    Récupère la couleur actuellement en production
    :param listener:    listener actuel
    :type listener:     dict
    :return:            BLUE/GREEN
    :rtype:             str
    """
    current_target_group_arn = __get_default_forward_target_group_arn_from_listener(listener)
    return __get_color_from_resource(current_target_group_arn).upper()


def __get_listener(listeners, ssl_enabled):
    """
    Récupère le listener qui contient les règles de redirection vers les services
    :param listeners:   liste de listener disponible
    :type listeners:    dict
    :param ssl_enabled: indique si le ssl est activé ou non
    :type ssl_enabled:  bool
    :return:            listener correspondant au port et protocol donné
    :rtype:             dict
    """
    protocol_port = constant.HTTPS_TUPLE if ssl_enabled else constant.HTTP_TUPLE
    # Careful if we got multiple http listener
    for listener in listeners['Listeners']:
        if (listener['Protocol'], listener['Port']) == protocol_port:
            return listener


def __get_default_forward_target_group_arn_from_listener(listener):
    # Careful if we got multiple forward target group
    for action in listener['DefaultActions']:
        if action['Type'] == 'forward':
            return action['TargetGroupArn']


def __get_color_from_resource(resource_arn):
    """
    Récupère la couleur d'une ressource donnée
    :param resource_arn:    Ressource AWS arn
    :type resource_arn:     str
    :return:                BLUE/GREEN
    :rtype:                 str
    """
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
            host = condition.get('HostHeaderConfig', None)
            if host:
                if all(__is_uncolored_host_header_value(v) for v in host['Values']):
                    uncolored_rules.append(rule)
    return uncolored_rules


def get_listener_rule_target_group_arn(listener_rule_arn):
    """
    Gets listener rule target group arn for forward rules
    :param listener_rule_arn
    :type listener_rule_arn: str
    :return: listener rule target group arn or None
    :rtype str
    """
    rule_details = elbv2_client.describe_rules(RuleArns=[listener_rule_arn])
    target_group_arn = None
    if len(rule_details['Rules']) > 0:
        try:
            target_group_arn = rule_details['Rules'][0]['Actions'][0]['TargetGroupArn']
        except Exception as e:
            logging.warning('No foward target group found for listener: ' + listener_rule_arn)
    return target_group_arn


def __is_uncolored_host_header_value(value):
    return constant.BLUE not in value.upper() and constant.GREEN not in value.upper()


# ~~~~~~~~~~~~~~~~ TARGET GROUP ~~~~~~~~~~~~~~~~


def get_target_group_name(target_group_arn):
    """
    Gets target group name from target group arn
    :param target_group_arn:
    :type target_group_arn: str
    :return: Target group name or None if not found
    :rtype: str
    """
    target_group_name = None
    target_group = elbv2_client.describe_target_groups(TargetGroupArns=[target_group_arn])
    if len(target_group['TargetGroups']) > 0:
        target_group_name = target_group['TargetGroups'][0]['TargetGroupName']
    return target_group_name
