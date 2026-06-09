import logging, requests
from random import randint, choice, gauss

from locust import HttpUser, task, LoadTestShape, events

# logging
logging.getLogger().setLevel(logging.INFO)

PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

def query_prometheus(promql_query):
    """Helper function to query Prometheus"""
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": promql_query})
        result = response.json()
        if result['data']['result']:
            return float(result['data']['result'][0]['value'][1])
        return None
    except Exception as e:
        print(f"  Error querying '{promql_query}': {e}")
        return None

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats
    total_requests = sum(stat.num_requests for stat in stats.entries.values())
    total_failures = sum(stat.num_failures for stat in stats.entries.values())
    test_duration = environment.stats.total.total_response_time / 1000
    
    throughput = total_requests / test_duration if test_duration > 0 else 0
    error_rate = (total_failures / total_requests * 100) if total_requests > 0 else 0
    
    print(f"\n{'='*60}")
    print(f"LOAD TEST RESULTS".center(60))
    print(f"{'='*60}")
    
    # Locust metrics
    print(f"\n📊 LOAD TEST METRICS:")
    print(f"  Total Requests: {total_requests}")
    print(f"  Total Failures: {total_failures}")
    print(f"  Test Duration: {test_duration:.2f} seconds")
    print(f"  Throughput: {throughput:.2f} req/sec")
    print(f"  Error Rate: {error_rate:.2f}%")
    
    # Query Prometheus for resource metrics
    print(f"\n🔍 QUERYING PROMETHEUS FOR SYSTEM METRICS...")
    
    # Requests per second
    rps = query_prometheus("sum(rate(teastore_http_server_request_count_total[1m]))")
    
    # Error rate from Prometheus
    error_rate_prom = query_prometheus("sum(rate(teastore_http_server_request_count_total{status=~\"5..\"}[1m]))")
    
    # P95 Latency
    p95_latency = query_prometheus("histogram_quantile(0.95, rate(teastore_http_server_duration_milliseconds_bucket[5m]))")
    
    # JVM Heap Memory
    heap_memory_bytes = query_prometheus("process_runtime_java_memory_usage_bytes{type=\"heap\"}")
    heap_memory_mb = heap_memory_bytes / (1024 * 1024) if heap_memory_bytes else None
    
    # CPU Usage
    cpu_usage = query_prometheus("avg(rate(process_runtime_java_cpu_usage_seconds[1m]))")
    cpu_percent = cpu_usage * 100 if cpu_usage else None
    
    # Active Threads
    active_threads = query_prometheus("jvm_threads_live_threads")
    
    # Display results
    print(f"\n📈 PROMETHEUS METRICS:")
    if rps is not None:
        print(f"  Requests/sec: {rps:.2f}")
    if error_rate_prom is not None:
        print(f"  Error Rate (5xx): {error_rate_prom:.4f} req/sec")
    if p95_latency is not None:
        print(f"  P95 Latency: {p95_latency:.2f} ms")
    if heap_memory_mb is not None:
        print(f"  Heap Memory: {heap_memory_mb:.2f} MB")
    if cpu_percent is not None:
        print(f"  CPU Usage: {cpu_percent:.2f}%")
    if active_threads is not None:
        print(f"  Active Threads: {int(active_threads)}")
    
    # Resource demand analysis
    print(f"\n💾 RESOURCE DEMAND ANALYSIS:")
    if heap_memory_mb and throughput > 0:
        print(f"  Memory per Request: {heap_memory_mb / throughput:.4f} MB/req")
    if cpu_percent and throughput > 0:
        print(f"  CPU per Request: {cpu_percent / throughput:.6f}% per req/sec")
    
    print(f"\n{'='*60}\n")

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
