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

import io.opentelemetry.api.common.Attributes;
import io.opentelemetry.api.metrics.Meter;
import io.opentelemetry.api.metrics.MeterProvider;
import io.opentelemetry.api.trace.Span;
import io.opentelemetry.api.trace.Tracer;
import io.opentelemetry.api.trace.TracerProvider;
import io.opentelemetry.context.Context;
import io.opentelemetry.context.Scope;
import jakarta.servlet.Filter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.FilterConfig;
import jakarta.servlet.ServletException;
import jakarta.servlet.ServletRequest;
import jakarta.servlet.ServletResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Servlet filter for OpenTelemetry instrumentation.
 * Collects metrics and traces for HTTP requests.
 * 
 * @author TeaStore Team
 */
public class TeaStoreOpenTelemetryFilter implements Filter {

	private static final Logger LOGGER = LoggerFactory.getLogger(TeaStoreOpenTelemetryFilter.class);

	private Tracer tracer;
	private Meter meter;
	private AtomicLong activeRequests;

	@Override
	public void init(FilterConfig filterConfig) throws ServletException {
		try {
			MeterProvider meterProvider = OpenTelemetryProvider.getMeterProvider();
			TracerProvider tracerProvider = OpenTelemetryProvider.getTracerProvider();

			this.tracer = tracerProvider.get("teastore.http");
			this.meter = meterProvider.get("teastore.http");
			this.activeRequests = new AtomicLong(0);

			// Register metrics
			meter.upDownCounterBuilder("http.requests.active")
				.setDescription("Number of active HTTP requests")
				.setUnit("1")
				.buildWithCallback(measurement -> measurement.record(activeRequests.get()));

			meter.counterBuilder("http.requests.total")
				.setDescription("Total number of HTTP requests")
				.setUnit("1")
				.build();

			meter.histogramBuilder("http.request.duration")
				.setDescription("HTTP request duration")
				.setUnit("ms")
				.build();

			LOGGER.info("OpenTelemetry Filter initialized");
		} catch (Exception e) {
			LOGGER.error("Failed to initialize OpenTelemetry Filter", e);
			throw new ServletException("Failed to initialize OpenTelemetry Filter", e);
		}
	}

	@Override
	public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
			throws IOException, ServletException {
		if (!(request instanceof HttpServletRequest) || !(response instanceof HttpServletResponse)) {
			chain.doFilter(request, response);
			return;
		}

		HttpServletRequest httpRequest = (HttpServletRequest) request;
		HttpServletResponse httpResponse = (HttpServletResponse) response;

		String method = httpRequest.getMethod();
		String path = httpRequest.getRequestURI();
		String spanName = method + " " + path;

		Span span = tracer.spanBuilder(spanName)
			.setAttribute("http.method", method)
			.setAttribute("http.url", path)
			.setAttribute("http.scheme", httpRequest.getScheme())
			.setAttribute("http.target", httpRequest.getRequestURI())
			.startSpan();

		activeRequests.incrementAndGet();
		long startTime = System.currentTimeMillis();

		try (Scope scope = span.makeCurrent()) {
			chain.doFilter(request, response);
		} catch (Exception e) {
			span.recordException(e);
			span.setAttribute("exception.type", e.getClass().getName());
			throw e;
		} finally {
			activeRequests.decrementAndGet();
			long duration = System.currentTimeMillis() - startTime;

			span.setAttribute("http.status_code", httpResponse.getStatus());
			span.end();

			// Record metrics
			if (meter != null) {
				Attributes attributes = Attributes.of(
					io.opentelemetry.api.common.AttributeKey.stringKey("http.method"), method,
					io.opentelemetry.api.common.AttributeKey.stringKey("http.url"), path,
					io.opentelemetry.api.common.AttributeKey.longKey("http.status_code"), 
						(long) httpResponse.getStatus()
				);

				meter.counterBuilder("http.requests.total")
					.build()
					.add(1, attributes);

				meter.histogramBuilder("http.request.duration")
					.build()
					.record(duration, attributes);
			}
		}
	}

	@Override
	public void destroy() {
		OpenTelemetryProvider.shutdown();
	}
}
