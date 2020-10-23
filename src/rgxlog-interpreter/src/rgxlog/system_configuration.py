# do not use this file to communicate between functions (except for initialization)

system_configuration = {
    'default_local_client_config': {
        'connection_retries': 3,
        'retry_sleep': 2,
        'min_port': 2 ** 15,
        'max_port': 2 ** 16
    },

    'default_remote_listener_config': {
        'ip': 'localhost',
        'port': 2 ** 15
    },
}
