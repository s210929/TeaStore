import logging
from random import randint, choice, gauss

from locust import HttpUser, task, LoadTestShape

# logging
logging.getLogger().setLevel(logging.INFO)


class UserBehavior(HttpUser):

    @task
    def load(self) -> None:
        """
        Simulates user behaviour.
        :return: None
        """
        logging.info("Starting user.")
        self.visit_home()
        self.login()
        self.browse()
        # 50/50 chance to buy
        choice_buy = choice([True, False])
        if choice_buy:
            self.buy()
        self.visit_profile()
        self.logout()
        logging.info("Completed user.")

    def visit_home(self) -> None:
        """
        Visits the landing page.
        :return: None
        """
        # load landing page
        res = self.client.get('/')
        if res.ok:
            logging.info("Loaded landing page.")
        else:
            logging.error(f"Could not load landing page: {res.status_code}")

    def login(self) -> None:
        """
        User login with random userid between 1 and 90.
        :return: categories
        """
        # load login page
        res = self.client.get('/login')
        if res.ok:
            logging.info("Loaded login page.")
        else:
            logging.error(f"Could not load login page: {res.status_code}")
        # login random user
        user = randint(1, 99)
        login_request = self.client.post("/loginAction", params={"username": user, "password": "password"})
        if login_request.ok:
            logging.info(f"Login with username: {user}")
        else:
            logging.error(
                f"Could not login with username: {user} - status: {login_request.status_code}")

    def browse(self) -> None:
        """
        Simulates random browsing behaviour.
        :return: None
        """
        # execute browsing action randomly up to 5 times
        for i in range(1, randint(2, 5)):
            # browses random category and page
            category_id = randint(2, 6)
            page = randint(1, 5)
            category_request = self.client.get("/category", params={"page": page, "category": category_id})
            if category_request.ok:
                logging.info(f"Visited category {category_id} on page 1")
                # browses random product
                product_id = randint(7, 506)
                product_request = self.client.get("/product", params={"id": product_id})
                if product_request.ok:
                    logging.info(f"Visited product with id {product_id}.")
                    cart_request = self.client.post("/cartAction", params={"addToCart": "", "productid": product_id})
                    if cart_request.ok:
                        logging.info(f"Added product {product_id} to cart.")
                    else:
                        logging.error(
                            f"Could not put product {product_id} in cart - status {cart_request.status_code}")
                else:
                    logging.error(
                        f"Could not visit product {product_id} - status {product_request.status_code}")
            else:
                logging.error(
                    f"Could not visit category {category_id} on page 1 - status {category_request.status_code}")

    def buy(self) -> None:
        """
        Simulates to buy products in the cart with sample user data.
        :return: None
        """
        # sample user data
        user_data = {
            "firstname": "User",
            "lastname": "User",
            "adress1": "Road",
            "adress2": "City",
            "cardtype": "volvo",
            "cardnumber": "314159265359",
            "expirydate": "12/2050",
            "confirm": "Confirm"
        }
        buy_request = self.client.post("/cartAction", params=user_data)
        if buy_request.ok:
            logging.info(f"Bought products.")
        else:
            logging.error("Could not buy products.")

    def visit_profile(self) -> None:
        """
        Visits user profile.
        :return: None
        """
        profile_request = self.client.get("/profile")
        if profile_request.ok:
            logging.info("Visited profile page.")
        else:
            logging.error("Could not visit profile page.")

    def logout(self) -> None:
        """
        User logout.
        :return: None
        """
        logout_request = self.client.post("/loginAction", params={"logout": ""})
        if logout_request.ok:
            logging.info("Successful logout.")
        else:
            logging.error(f"Could not log out - status: {logout_request.status_code}")

class CustomLoadShape(LoadTestShape):
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 60:
            # Ramp up phase: gradually increase with random variations
            base_users = run_time
            # Add random fluctuation (±30% of base)
            user_count = max(1, int(base_users + gauss(0, base_users * 0.3)))
            spawn_rate = 2
        elif run_time < 180:
            # Steady state: fluctuate randomly between 50-150 users
            user_count = randint(50, 150)
            spawn_rate = 3
        elif run_time < 240:
            # Wind down phase: decrease with random variations
            remaining_time = 240 - run_time
            base_users = remaining_time
            user_count = max(1, int(base_users + gauss(0, base_users * 0.3)))
            spawn_rate = 2
        else:
            return None
        
        return (user_count, spawn_rate)
