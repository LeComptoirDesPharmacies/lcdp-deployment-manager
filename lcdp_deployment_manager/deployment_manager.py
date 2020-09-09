import time
from functools import reduce
from . import constant as constant
from . import common as common


###
#   Classe permettant de gérer le déployement
###
class DeploymentManager:
    alb = None
    http_listener = None
    default_target_group = None
    rules = []
    repositories = []
    prod_color = None
    blue_environment = {}
    green_environment = {}

    # Clients
    elbv2_client = None

    def __init__(self, elbv2_client, alb, http_listener, rules, repositories,
                 prod_color, blue_environment, green_environment):
        self.elbv2_client = elbv2_client
        self.alb = alb
        self.http_listener = http_listener
        self.rules = rules
        self.repositories = repositories
        self.prod_color = prod_color
        self.blue_environment = blue_environment
        self.green_environment = green_environment

    # Constuit une action pour le listener
    def __build_forward_actions(self, target_group_arn):
        return {
            "Type": "forward",
            "TargetGroupArn": target_group_arn,
            "Order": 1
        }

    def get_production_environment(self):
        return self.blue_environment if self.prod_color == constant.BLUE else self.green_environment

    def get_pre_production_environment(self):
        return self.green_environment if self.prod_color == constant.BLUE else self.blue_environment

    def modify_listener_default_target_group(self, target_group_arn):
        return self.elbv2_client.modify_listener(
            ListenerArn=self.http_listener['ListenerArn'],
            DefaultActions=[self.__build_forward_actions(target_group_arn)]
        )

    def update_rule_target_group(self, rule_type, rule_color, new_target_group_arn):
        targeted_rule = self.__get_rule_with_type_and_color(rule_type, rule_color)
        if targeted_rule:
            return self.__modify_rule_target_group(targeted_rule, new_target_group_arn)

    def __modify_rule_target_group(self, rule, target_group_arn):
        return self.elbv2_client.modify_rule(
            RuleArn=rule['RuleArn'],
            Actions=[self.__build_forward_actions(target_group_arn)]
        )

    def __get_rule_with_type_and_color(self, tg_type, color):
        expected = (tg_type.upper(), color.upper())
        for rule in self.rules:
            for action in rule['Actions']:
                if action['Type'] == 'forward':
                    tap_tpl = common.get_type_and_color_for_resource(action['TargetGroupArn'], self.elbv2_client)
                    if tap_tpl == expected:
                        return rule

    # Ajout d'un tag a tous les repository d'un environement
    def add_tag_to_repositories(self, tag):
        for r in self.repositories:
            r.add_tag(tag)


###
#   Classe contenant les informations utiles d'un environment blue ou green
###
class Environment:
    ecs_client = None
    application_autoscaling_client = None
    color = None
    cluster_name = None
    ecs_services = []
    gw_target_group_arn = None
    monolith_target_group_arn = None
    default_target_group_arn = None

    def __init__(self, ecs_client, application_autoscaling_client, color, cluster_name, ecs_services,
                 gw_target_group_arn, monolith_target_group_arn, default_target_group_arn):
        self.ecs_client = ecs_client
        self.application_autoscaling_client = application_autoscaling_client
        self.color = color
        self.cluster_name = cluster_name
        self.ecs_services = ecs_services
        self.gw_target_group_arn = gw_target_group_arn
        self.monolith_target_group_arn = monolith_target_group_arn
        self.default_target_group_arn = default_target_group_arn

    # Démarre tous les services
    def start_up_services(self, desired_count=None):
        for s in self.ecs_services:
            s.start(desired_count)
            service_arn = str(s)
            resource_id = service_arn.split(':')[5]
            tags = common.get_ecs_tags_for_resource(service_arn, self.ecs_client)
            for i in range(len(tags)):
                if tags[i].get("key") == "max_capacity":
                    max_capacity = tags[i].get("value")
            response = self.application_autoscaling_client.register_scalable_target(
                ServiceNamespace=constant.ECS_SERVICE_NAMESPACE,
                ResourceId=resource_id,
                ScalableDimension=constant.DEFAULT_SCALABLE_DIMENSION,
                # TODO: Use a variable to set MinCapacity/MaxCapacity values
                MinCapacity=2,
                MaxCapacity=int(max_capacity)
            )
            print("Started service: '{}', Updated Capacities => MaxCapacity: {} / MinCapacity: 2, response: {}"
                  .format(s, max_capacity, response))
        # Wait for all service receive startup
        time.sleep(10)

    # Eteint tous les services
    def shutdown_services(self):
        for s in self.ecs_services:
            s.shutdown()
            service_arn = str(s)
            resource_id = service_arn.split(':')[5]
            tags = common.get_ecs_tags_for_resource(service_arn, self.ecs_client)
            for i in range(len(tags)):
                if tags[i].get("key") == "max_capacity":
                    max_capacity = tags[i].get("value")
            response = self.application_autoscaling_client.register_scalable_target(
                ServiceNamespace=constant.ECS_SERVICE_NAMESPACE,
                ResourceId=resource_id,
                ScalableDimension=constant.DEFAULT_SCALABLE_DIMENSION,
                # TODO: Use a variable to set MinCapacity/MaxCapacity values
                MinCapacity=0,
                MaxCapacity=int(max_capacity)
            )
            print("Stopped service: '{}', Updated Capacities => MaxCapacity: {} / MinCapacity: 0, response: {}"
                  .format(s, max_capacity, response))
        # Wait for all service receive shutdown
        time.sleep(10)

    def get_unhealthy_services(self):
        return list(filter(lambda s: not s.is_service_healthy(), self.ecs_services))

    # Vérifie que tous les services sont healthy
    def all_services_are_healthy(self):
        return all(s.is_service_healthy() for s in self.ecs_services)

    # Attend que tous les services soit healthy
    def wait_for_services_health(self):
        retry = 1
        print("Waiting {} seconds before first try".format(constant.HEALTHCHECK_SLEEPING_TIME))
        time.sleep(constant.HEALTHCHECK_SLEEPING_TIME)
        while not self.all_services_are_healthy() and constant.HEALTHCHECK_RETRY_LIMIT >= retry:
            print("Retry number {} all services hasnt healthy sleeping {} seconds before retry"
                  .format(retry, constant.HEALTHCHECK_SLEEPING_TIME))
            retry = retry + 1
            time.sleep(constant.HEALTHCHECK_SLEEPING_TIME)
        if constant.HEALTHCHECK_RETRY_LIMIT < retry:
            print("Tried {} but retry limit has been reach before all services been healthy".format(retry))
            # Raise exception
            unhealthy_sve = reduce(lambda a, b: a.service_arn+','+b.service_arn, self.get_unhealthy_services())
            raise Exception("Unable to deploy, services still unhealthy. Unhealthy Services : {}".format(unhealthy_sve))
        else:
            print("Tried {} and all service are now healthy".format(retry))


###
# Classe qui map un ECS aws
###
class EcsService:
    cluster_name = None
    service_arn = None
    task = []
    ecs_client = None
    service_healthy = False

    def __init__(self, ecs_client, cluster_name, service_arn):
        self.ecs_client = ecs_client
        self.cluster_name = cluster_name
        self.service_arn = service_arn

    def __get_task(self):
        tasks = self.ecs_client.list_tasks(
            cluster=self.cluster_name,
            serviceName=self.service_arn,
            # TODO: Review if one day we got more than 100 ecs tasks !
            maxResults=100
        )
        return tasks['taskArns']

    def start(self, desired_count=None):
        if not desired_count:
            desired_count = constant.DEFAULT_DESIRED_COUNT
        print('Start service {} with {} instances'.format(self.service_arn, desired_count))
        return self.ecs_client.update_service(
            cluster=self.cluster_name,
            service=self.service_arn,
            desiredCount=desired_count,
            forceNewDeployment=True
        )

    def shutdown(self):
        print('Shutdown service {}'.format(self.service_arn))
        return self.ecs_client.update_service(
            cluster=self.cluster_name,
            service=self.service_arn,
            desiredCount=0
        )

    def is_service_healthy(self):
        if not self.service_healthy:
            self.service_healthy = self.__check_service_health()
        return self.service_healthy

    def __check_service_health(self):
        tasks = self.__get_task()
        if not tasks:
            return False
        detailed_task = self.ecs_client.describe_tasks(
            cluster=self.cluster_name,
            tasks=tasks
        )
        nb_healthy_task = len(list(filter(lambda x: x['healthStatus'] == 'HEALTHY', detailed_task['tasks'])))
        is_healthy = nb_healthy_task >= constant.DEFAULT_DESIRED_COUNT
        if is_healthy:
            print('{} has reach the healthy state'.format(self.service_arn))
        else:
            print('{} is not healthy, only has {} task(s) healthy and {} healthy tasks are required to pass'
                  .format(self.service_arn, nb_healthy_task, constant.DEFAULT_DESIRED_COUNT))
        return is_healthy

    def __str__(self):
        return self.service_arn


###
# Classe qui map un ECR aws
###
class Repository:
    name = None
    image = None
    manifest = None
    ecr_client = None

    def __init__(self, ecr_client, name, image, manifest):
        self.ecr_client = ecr_client
        self.name = name
        self.image = image
        self.manifest = manifest

    def add_tag(self, tag):
        try:
            print('Adding tag {} to image {} in repository {}'.format(tag, self.image, self.name))
            new_image = self.ecr_client.put_image(
                repositoryName=self.name,
                imageManifest=self.manifest,
                imageTag=tag
            )
            return new_image
        except self.ecr_client.exceptions.ImageAlreadyExistsException:
            print('Image {} in repository {} already exist with tag {}'.format(self.image, self.name, tag))

