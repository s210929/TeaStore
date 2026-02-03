from locust import HttpUser, task, between
import random
import logging

# logging
logging.getLogger().setLevel(logging.INFO)

class RecommenderUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def get_recommendation(self) -> None:
        user_id = random.randint(1, 1000)
        logging.info("Get recommendation")
        with self.client.get(
            f"/recommendation/{user_id}",
            name="/recommendation/{userId}",
            catch_response=True
        ) as response:
            if response.status_code != 200:
                response.failure(f"Status {response.status_code}")
                logging.info("Recommendation failed")
        logging.info("Recommendation complete")