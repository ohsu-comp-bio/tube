import yaml


def get_sql_to_hdfs_config(config):
    return {
        'input': {
            'jdbc': config['JDBC'],
            'username': config['DB_USERNAME'],
            'password': config['DB_PASSWORD'],
        },
        'output': config['HDFS_DIR']
    }


def list_to_file(lst, file_path):
    with open(file_path, 'w') as f:
        f.write('\n'.join(lst))


def get_resource_paths_from_yaml(useryaml_file):
    """
    Get all resource paths from user yaml file
    """
    if not useryaml_file:
        print("Can not find user.yaml file")
        return {}

    with open(useryaml_file, 'r') as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as e:
            print("Can not read {}. Detail {}".format(useryaml_file, e))
            return {}
    
    results = {}
    for _, user in data.get("users", {}).iteritems():
        projects = user.get("projects", [])
        if not isinstance(projects, list):
            projects = [projects]
        for pr in projects:
            if "resource" in pr:
                results[pr.get("auth_id")] = pr["resource"]
    
    # if user_project_to_resource is in user yaml
    json_data = data.get("authz", data.get("rbac"))
    if json_data:
        get_resource_path_from_json(results, json_data)
    return results


def get_resource_path_from_json(results, json_data):
    user_project_to_resource = json_data.get('user_project_to_resource', {})
    for project in user_project_to_resource:
        results[project] = user_project_to_resource[project]
    return results
