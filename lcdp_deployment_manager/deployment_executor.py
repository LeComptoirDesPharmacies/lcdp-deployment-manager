import time

from . import constant as constant
from . import manage_ecs as ecs_manager


SHUTDOWN_CHECK_INTERVAL = 15  # seconds between polls
SHUTDOWN_TIMEOUT = 900  # 15 minutes max, same as Lambda timeout budget


def _wait_for_active_jobs_to_complete(environment):
    """Wait for all smuggler jobs to complete before shutting down, max 10 minutes."""
    # start_time = time.time()
    # while True:
    #     metrics = environment.get_active_and_pending_smuggler_jobs()
    #     active_jobs = metrics.get('active_jobs', 0)
    #
    #     if active_jobs == 0:
    #         print("No active smuggler jobs, safe to proceed with shutdown")
    #         return
    #
    #     elapsed = int(time.time() - start_time)
    #     if elapsed > 600:
    raise Exception(
        "\n"
        "/!\\ /!\\ /!\\ ECHEC DU DEPLOIEMENT /!\\ /!\\ /!\\\n"
        "\n"
        "{} job(s) smuggler toujours actif(s) apres 10 minutes d'attente.\n"
        "\n"
        "=> RELANCEZ LE DEPLOIEMENT.\n"
        "\n"
        "/!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\\n".format(active_jobs)
    )

        # print("Waiting for smuggler jobs to complete: {} active ({}s / 600s)".format(active_jobs, elapsed))
        # time.sleep(SHUTDOWN_CHECK_INTERVAL)


def ensure_environment_is_shut_down(environment):
    """Ensure all services in the environment have 0 running tasks before proceeding.
    This prevents old version tasks from coexisting with new ones after image tags are updated."""
    _wait_for_active_jobs_to_complete(environment)

    print("Sending shutdown to all {} services in {} environment".format(
        len(environment.ecs_services), environment.color))
    environment.shutdown_services()

    start_time = time.time()
    while (time.time() - start_time) < SHUTDOWN_TIMEOUT:
        running_task_count = 0
        services_with_tasks = []
        for svc in environment.ecs_services:
            tasks = svc.get_running_task_arns()
            if tasks:
                running_task_count += len(tasks)
                services_with_tasks.append('{} ({})'.format(svc.service_arn, len(tasks)))

        if running_task_count == 0:
            elapsed = int(time.time() - start_time)
            print("Pre-prod environment fully shut down in {}s, 0 tasks running".format(elapsed))
            return

        elapsed = int(time.time() - start_time)
        print("Waiting for pre-prod shutdown: {} task(s) still running ({}s / {}s) - services: {}".format(
            running_task_count, elapsed, SHUTDOWN_TIMEOUT, ', '.join(services_with_tasks)))
        time.sleep(SHUTDOWN_CHECK_INTERVAL)

    raise Exception(
        "\n"
        "/!\\ /!\\ /!\\ ECHEC DU SHUTDOWN /!\\ /!\\ /!\\\n"
        "\n"
        "Le pre-prod a encore {} task(s) running apres {} secondes d'attente.\n"
        "Services concernes : {}\n"
        "\n"
        "=> RELANCEZ LE DEPLOIEMENT. Si le probleme persiste, verifiez l'etat des services dans la console ECS.\n"
        "\n"
        "/!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\ /!\\\n".format(
            running_task_count, SHUTDOWN_TIMEOUT, ', '.join(services_with_tasks))
    )


# Démarre tous les services d'un environement et attend qu'il soit entièrement up
def start_environment_and_wait_for_health(environment, verify_rollout=False):
    if verify_rollout:
        print("Rollout verification enabled for all {} services".format(len(environment.ecs_services)))
        environment.enable_rollout_verification()
    print("Starting all {} services in {} environment".format(len(environment.ecs_services), environment.color))
    environment.start_up_services()
    print("Waiting for all services to be healthy{}...".format(
        " and rollout complete" if verify_rollout else ""))
    environment.wait_for_services_health()


# Passe d'un environnement à l'autre en modifiant les targets groups des règles du listener
def do_balancing(deployment_manager, from_environment, to_environment):
    print("Do balancing from environment {} to environment {}".format(from_environment.color, to_environment.color))
    deployment_manager.update_rule_target_group(
        expected_rule_type=from_environment.target_group_type,
        expected_rule_color=from_environment.color,
        new_target_group_arn=to_environment.target_group_arn
    )


def deploy_services_of_repositories_name(environment, repositories_name, verify_rollout=False):
    print("Deploy services for repositories: {}".format(repositories_name))

    repo_name_service_map = ecs_manager.get_map_of_repo_name_service(environment.color, environment.cluster_name)

    # Collect environment services that match the repositories to deploy
    services_to_start = []
    for repo_name in repositories_name:
        if repo_name in repo_name_service_map:
            target_arn = repo_name_service_map[repo_name].service_arn
            # Find the matching service in the environment's own list
            for svc in environment.ecs_services:
                if svc.service_arn == target_arn:
                    services_to_start.append(svc)
                    break

    print("Matched {} services to redeploy out of {} repositories".format(
        len(services_to_start), len(repositories_name)))

    if verify_rollout and services_to_start:
        print("Rollout verification enabled for {} services".format(len(services_to_start)))
        environment.enable_rollout_verification(services=services_to_start)

    if services_to_start:
        for service in services_to_start:
            print("Start service {}".format(service.resource_id))
            service.start()

        # Wait only for the deployed services to be healthy (not all services in the environment)
        time.sleep(10)
        print("Waiting for {} redeployed services to be healthy{}...".format(
            len(services_to_start), " and rollout complete" if verify_rollout else ""))
        environment.wait_for_services_health(services=services_to_start)
    else:
        print("No matching services found to redeploy")
