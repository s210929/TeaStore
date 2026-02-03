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
        response = self.client.post("/tools.descartes.teastore.recommender/rest/recommendsingle", params={data})
        # with self.client.post(
        #     f"/recommendation/{user_id}",
        #     name="/recommendation/{userId}",
        #     catch_response=True
        # ) as response:
        #     if response.status_code != 200:
        #         response.failure(f"Status {response.status_code}")
        #         logging.info("Recommendation failed")
        logging.info(f"Response: {response}")