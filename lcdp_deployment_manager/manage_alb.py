import boto3
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


def get_alb_arn_by_name_contains(str_contained_in_name):
    """
    Récupère l'alb dont le nom contient une str
    :param str_contained_in_name:    La str contenue dans le nom de l'alb
    :type str_contained_in_name:     str
    :return:            arn du load balancer trouvé
    :rtype:             str
    """
    all_albs = elbv2_client.describe_load_balancers(LoadBalancerArns=[])
    alb_arn = None
    for alb in all_albs['LoadBalancers']:
        if str_contained_in_name in alb['LoadBalancerName']:
            alb_arn = alb['LoadBalancerArn']
    return alb_arn


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


def get_alb_rules_arns_by_hosts_starts_with(alb_arn, hosts_starts_with):
    """
    Récupère toutes les regles listener d'un alb
    :param alb_arn: L'arn de l'alb
    :type alb_arn: str
    :param hosts_starts_with: Les debuts des noms des host des regles
    :type: hosts_starts_with: list of str
    :return: Les arns recherchés
    :rtype: list of str
    """
    listeners = elbv2_client.describe_listeners(
        LoadBalancerArn=alb_arn
    )
    public_rules_arns = []
    if 'Listeners' in listeners:
        for listener in listeners['Listeners']:
            for host_starts_with in hosts_starts_with:
                public_rules_arns.extend(get_listener_rules_by_host_starts_with(listener['ListenerArn'],
                                                                                host_starts_with))
    return public_rules_arns


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


def get_listener_rules_by_host_starts_with(listener_arn, host_starts_with):
    """
    Récupère les règles d'un listener en fonction du host starts with
    :param listener_arn:    listener actuel
    :type listener_arn:     str
    :param host_starts_with:    le debut de host recherché
    :type host_starts_with:     str
    :return:            Liste des arns des regles trouvées
    :rtype:             list of str
    """
    all_rules = elbv2_client.describe_rules(
        ListenerArn=listener_arn
    )
    public_rules_arns = []
    if 'Rules' in all_rules:
        for rule in all_rules['Rules']:
            for condition in rule['Conditions']:
                if 'Values' in condition:
                    for rule_value in condition['Values']:
                        if rule_value.startswith(host_starts_with):
                            public_rules_arns.append(rule['RuleArn'])
    return public_rules_arns


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
            host = condition['HostHeaderConfig']
            if all(__is_uncolored_host_header_value(v) for v in host['Values']):
                uncolored_rules.append(rule)
    return uncolored_rules


def set_listener_rule_to_target_group(rule_arn, target_group_arn):
    """
    Assigne à une regle listener un target group
    :param rule_arn:    la regle du listener
    :type rule_arn:     str
    :param target_group_arn:    le target group
    :type target_group_arn:     str
    """
    return elbv2_client.modify_rule(
        RuleArn=rule_arn,
        Actions=[
            {
                'Type': 'forward',
                'TargetGroupArn': target_group_arn
            },
        ]
    )


def __is_uncolored_host_header_value(value):
    return constant.BLUE not in value.upper() and constant.GREEN not in value.upper()


# ~~~~~~~~~~~~~~~~ TARGET GROUP ~~~~~~~~~~~~~~~~

def get_target_group_arn_by_name(target_group_name):
    """
    Get target group arn by target group name
    :param target_group_name:
    :type target_group_name: str
    :return: target group arn or None if not found
    :rtype: str
    """
    target_group_arn = None
    target_groups = elbv2_client.describe_target_groups()
    for target_group in target_groups['TargetGroups']:
        if 'TargetGroupArn' in target_group \
                and 'TargetGroupName' in target_group \
                and target_group_name == target_group['TargetGroupName']:
            target_group_arn = target_group['TargetGroupArn']
    return target_group_arn


def get_running_target_group_arn_by_name_contains(target_group_name_contains):
    """
    Recupere les targets groups (BLUE ou GREEN) actifs
    :param target_group_name_contains: la chaine de caractères contenu dans le nom du target group
    :type target_group_name_contains: str
    :return:
    """
    target_group_arn = []
    target_groups = elbv2_client.describe_target_groups()
    for target_group in target_groups['TargetGroups']:
        if 'TargetGroupArn' in target_group \
                and 'TargetGroupName' in target_group \
                and target_group_name_contains in target_group['TargetGroupName']:
            targets = elbv2_client.describe_target_health(TargetGroupArn=target_group['TargetGroupArn'])
            if targets['TargetHealthDescriptions'] and len(targets['TargetHealthDescriptions']) > 0:
                target_group_arn.append(target_group['TargetGroupArn'])
    return target_group_arn
