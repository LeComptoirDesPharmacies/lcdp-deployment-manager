from .deployment_manager \
    import DeploymentManager, Repository, Environment, EcsService
from . import manage_ecr as ecr_manager
from . import manage_alb as alb_manager
from . import manage_ecs as ecs_manager
from . import constant as constant
import boto3

# Client
ecr_client = boto3.client('ecr')
ecs_client = boto3.client('ecs')
elbv2_client = boto3.client('elbv2')
application_autoscaling_client = boto3.client('application-autoscaling')


def build_deployment_manager(alb_name, cluster_name, img_deploy_tag, ssl_enabled, workspace):
    alb = alb_manager.get_alb_from_aws(alb_name)
    listener = alb_manager.get_current_listener(alb['LoadBalancerArn'], ssl_enabled)
    rules = alb_manager.get_uncolored_rules(listener)
    prod_color = alb_manager.get_production_color(listener)
    current_target_group_type = alb_manager.get_production_type(listener)
    repositories = list(
        map(lambda x: __build_repository(x, img_deploy_tag), ecr_manager.get_service_repositories_name()))
    green_environment = __build_environment(constant.GREEN, current_target_group_type,
                                            cluster_name, workspace)
    blue_environment = __build_environment(constant.BLUE, current_target_group_type,
                                           cluster_name, workspace)

    return DeploymentManager(
        elbv2_client=elbv2_client,
        alb=alb,
        http_listener=listener,
        rules=[r for r in rules if r],
        prod_color=prod_color,
        current_target_group_type=current_target_group_type,
        repositories=[r for r in repositories if r],
        green_environment=green_environment,
        blue_environment=blue_environment,
    )


def __build_repository(repository_name, tag):
    image = ecr_manager.get_repository_image_for_tag(repository_name, tag)
    if image:
        image_manifest = ecr_manager.get_image_manifest(repository_name, image)
        return Repository(
            name=repository_name,
            ecr_client=ecr_client,
            image=image,
            manifest=image_manifest
        )


def build_service(cluster_name, service_arn):
    return EcsService(ecs_client=ecs_client, application_autoscaling_client=application_autoscaling_client,
                      cluster_name=cluster_name, service_arn=service_arn,
                      max_capacity=ecs_manager.get_service_max_capacity_from_service_arn(service_arn),
                      resource_id=ecs_manager.get_service_resource_id_from_service_arn(service_arn))


def __build_environment(color, target_group_type, cluster_name, workspace):
    services_arn = ecs_manager.get_services_arn_for_color(color, cluster_name)
    ecs_services = list(map(
        lambda x: build_service(cluster_name, x),
        services_arn
    ))

    return Environment(
        workspace=workspace,
        color=color,
        target_group_type=target_group_type,
        cluster_name=cluster_name,
        ecs_client=ecs_client,
        ecs_services=[s for s in ecs_services if s],
        target_group_arn=alb_manager.get_target_group_with_type_color_and_workspace(
            target_group_type, color, workspace
        )
    )
