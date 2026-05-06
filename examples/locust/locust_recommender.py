from locust import HttpUser, task, between, LoadTestShape
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


class StepLoadShape(LoadTestShape):
    step_time = 60
    step_load = 10
    max_steps = 10

    def tick(self):
        run_time = self.get_run_time()

        current_step = int(run_time / self.step_time) + 1
        if current_step > self.max_steps:
            return None

        user_count = current_step * self.step_load
        spawn_rate = self.step_load

        return (user_count, spawn_rate)