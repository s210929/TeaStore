from locust import HttpUser, task, between
import random
import logging

# logging
logging.getLogger().setLevel(logging.INFO)

class RecommenderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_recommendation(self) -> None:
        user_id = random.randint(1, 99)
        data = {"item": 1,
                "uid": user_id}
        response = self.client.post("/tools.descartes.teastore.recommender/rest/recommendsingle", json={})
        if (response.ok):
            logging.info(f"Response ok: {response.status_code}")
        else:
            logging.info(f"Response not ok: {response.status_code}")