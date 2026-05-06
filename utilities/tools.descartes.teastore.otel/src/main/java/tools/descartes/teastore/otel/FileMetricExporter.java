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

import io.opentelemetry.sdk.common.CompletableResultCode;
import io.opentelemetry.sdk.metrics.InstrumentType;
import io.opentelemetry.sdk.metrics.data.AggregationTemporality;
import io.opentelemetry.sdk.metrics.data.MetricData;
import io.opentelemetry.sdk.metrics.export.MetricExporter;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * File-based metric exporter for OpenTelemetry.
 * Exports metrics to a JSON file.
 * 
 * @author TeaStore Team
 */
public class FileMetricExporter implements MetricExporter {

	private static final Logger LOGGER = LoggerFactory.getLogger(FileMetricExporter.class);
	private final String filePath;
	private final ObjectMapper objectMapper;
	private final List<Map<String, Object>> metricsBuffer = new ArrayList<>();

	/**
	 * Create a new FileMetricExporter.
	 * 
	 * @param filePath path to the metrics file
	 */
	public FileMetricExporter(String filePath) {
		this.filePath = filePath;
		this.objectMapper = new ObjectMapper();
		this.objectMapper.enable(SerializationFeature.INDENT_OUTPUT);
		
		// Create parent directories if needed
		try {
			File file = new File(filePath);
			Files.createDirectories(Paths.get(file.getParent()));
		} catch (IOException e) {
			LOGGER.warn("Failed to create metrics directory", e);
		}
	}

	@Override
	public CompletableResultCode export(Collection<MetricData> metrics) {
		try {
			synchronized (metricsBuffer) {
				for (MetricData metric : metrics) {
					Map<String, Object> metricMap = convertMetricToMap(metric);
					metricsBuffer.add(metricMap);
				}
			}
			writeMetricsToFile();
			return CompletableResultCode.ofSuccess();
		} catch (Exception e) {
			LOGGER.error("Failed to export metrics", e);
			return CompletableResultCode.ofFailure();
		}
	}

	@Override
	public CompletableResultCode flush() {
		try {
			writeMetricsToFile();
			return CompletableResultCode.ofSuccess();
		} catch (Exception e) {
			LOGGER.error("Failed to flush metrics", e);
			return CompletableResultCode.ofFailure();
		}
	}

	@Override
	public CompletableResultCode shutdown() {
		try {
			flush();
			return CompletableResultCode.ofSuccess();
		} catch (Exception e) {
			LOGGER.error("Failed to shutdown metrics exporter", e);
			return CompletableResultCode.ofFailure();
		}
	}

	@Override
	public AggregationTemporality getAggregationTemporality(InstrumentType instrumentType) {
		return AggregationTemporality.CUMULATIVE;
	}

	private void writeMetricsToFile() throws IOException {
		synchronized (metricsBuffer) {
			if (metricsBuffer.isEmpty()) {
				return;
			}

			Map<String, Object> output = new HashMap<>();
			output.put("timestamp", Instant.now().toString());
			output.put("metrics", new ArrayList<>(metricsBuffer));

			try (FileWriter writer = new FileWriter(filePath)) {
				writer.write(objectMapper.writeValueAsString(output));
				LOGGER.debug("Metrics written to file: {}", filePath);
			}
		}
	}

	private Map<String, Object> convertMetricToMap(MetricData metric) {
		Map<String, Object> map = new HashMap<>();
		map.put("name", metric.getName());
		map.put("description", metric.getDescription());
		map.put("unit", metric.getUnit());
		map.put("type", metric.getType().toString());
		map.put("timestamp", Instant.now().toString());

		// Extract data points
		List<Map<String, Object>> dataPoints = new ArrayList<>();
		metric.getData().getPoints().forEach(point -> {
			Map<String, Object> pointMap = new HashMap<>();
			pointMap.put("timestamp", point.getStartTime().toString());
			pointMap.put("endTimestamp", point.getEndTime().toString());
			
			// Extract value based on metric type
			if (point.hasValue()) {
				pointMap.put("value", point.getValue());
			}
			
			dataPoints.add(pointMap);
		});
		map.put("dataPoints", dataPoints);

		return map;
	}
}
