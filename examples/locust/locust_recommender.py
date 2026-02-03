from locust import HttpUser, task, between
import random
import logging

# logging
logging.getLogger().setLevel(logging.INFO)

class RecommenderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def recommend_single(self) -> None:

        content = {
            "productId": random.randint(1, 100),
            "quantity": 1
        }
        response = self.client.post("/tools.descartes.teastore.recommender/rest/recommendsingle", params={"uid": random.randint(1, 99)}, json=content, name="singlerecommend")
        if (response.ok):
            logging.info(f"Response ok: {response.status_code}")
        else:
            logging.info(f"Response not ok: {response.status_code}")