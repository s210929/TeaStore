/**
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package tools.descartes.teastore.otel;

import io.opentelemetry.api.OpenTelemetry;
import io.opentelemetry.api.metrics.MeterProvider;
import io.opentelemetry.api.trace.TracerProvider;
import io.opentelemetry.sdk.OpenTelemetrySdk;
import io.opentelemetry.sdk.metrics.SdkMeterProvider;
import io.opentelemetry.sdk.metrics.export.PeriodicMetricReader;
import io.opentelemetry.sdk.trace.SdkTracerProvider;
import io.opentelemetry.sdk.trace.export.BatchSpanProcessor;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * OpenTelemetry configuration provider.
 * 
 * @author TeaStore Team
 */
public class OpenTelemetryProvider {

	private static final Logger LOGGER = LoggerFactory.getLogger(OpenTelemetryProvider.class);
	private static OpenTelemetry instance = null;

	/**
	 * Get or initialize OpenTelemetry singleton.
	 * 
	 * @return OpenTelemetry instance
	 */
	public static synchronized OpenTelemetry getInstance() {
		if (instance == null) {
			instance = initializeOpenTelemetry();
		}
		return instance;
	}

	/**
	 * Initialize OpenTelemetry with file-based metrics.
	 * 
	 * @return initialized OpenTelemetry instance
	 */
	private static OpenTelemetry initializeOpenTelemetry() {
		try {
			LOGGER.info("Initializing OpenTelemetry...");

			// Create a periodic metric reader that exports to a file
			PeriodicMetricReader metricReader = PeriodicMetricReader.builder(
					new FileMetricExporter("/metrics/metrics.json"))
				.setIntervalMillis(15000) // Export every 15 seconds
				.build();

			// Create SDK components
			SdkMeterProvider meterProvider = SdkMeterProvider.builder()
				.addMetricReader(metricReader)
				.build();

			SdkTracerProvider tracerProvider = SdkTracerProvider.builder()
				.build();

			// Create OpenTelemetry SDK
			OpenTelemetrySdk sdk = OpenTelemetrySdk.builder()
				.setMeterProvider(meterProvider)
				.setTracerProvider(tracerProvider)
				.buildAndRegisterGlobal();

			LOGGER.info("OpenTelemetry initialized successfully");
			return sdk;
		} catch (Exception e) {
			LOGGER.error("Failed to initialize OpenTelemetry", e);
			throw new RuntimeException("Failed to initialize OpenTelemetry", e);
		}
	}

	/**
	 * Get the MeterProvider.
	 * 
	 * @return MeterProvider instance
	 */
	public static MeterProvider getMeterProvider() {
		return getInstance().getMeterProvider();
	}

	/**
	 * Get the TracerProvider.
	 * 
	 * @return TracerProvider instance
	 */
	public static TracerProvider getTracerProvider() {
		return getInstance().getTracerProvider();
	}

	/**
	 * Shutdown OpenTelemetry.
	 */
	public static synchronized void shutdown() {
		if (instance instanceof OpenTelemetrySdk) {
			LOGGER.info("Shutting down OpenTelemetry...");
			((OpenTelemetrySdk) instance).close();
		}
	}
}
