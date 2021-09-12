import json
import os


class DataManager:
    def __init__(self):
        pass

    @staticmethod
    def is_server_opted_in(server_id: int) -> bool:
        with open(os.path.join('assets', 'server-opt-in.json'), 'r') as f:
            data_opt_in = json.load(f)

        return server_id in data_opt_in['server_ids']
