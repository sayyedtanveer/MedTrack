from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, StreamingResponse
import time
import logging
from backend.app.infrastructure.persistence.database import (
    query_count_ctx,
    sql_time_ctx,
    conn_checkout_time_ctx,
    query_tables_ctx
)

logger = logging.getLogger("performance_profiler")
# Ensure the logger shows up
logger.setLevel(logging.INFO)

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Reset context variables for this request
        query_count_ctx.set(0)
        sql_time_ctx.set(0.0)
        conn_checkout_time_ctx.set(0.0)
        query_tables_ctx.set([])
        
        request.state.jwt_decode_time = 0.0
        request.state.auth_db_time = 0.0

        start_time = time.monotonic()
        
        response = await call_next(request)
        
        total_time_ms = (time.monotonic() - start_time) * 1000
        
        # Calculate payload size if available
        payload_size = 0
        if hasattr(response, "body"):
            payload_size = len(response.body)
        
        # Detect N+1 by looking for duplicated tables
        tables = query_tables_ctx.get()
        table_counts = {}
        for t in tables:
            t_lower = t.lower()
            table_counts[t_lower] = table_counts.get(t_lower, 0) + 1
        
        n_plus_one_warnings = []
        for table, count in table_counts.items():
            if count > 2:  # Arbitrary threshold for N+1 detection
                n_plus_one_warnings.append(f"{table}({count}x)")
        
        n_plus_one_str = f" [N+1 Warning: {', '.join(n_plus_one_warnings)}]" if n_plus_one_warnings else ""
        
        # Log the metrics
        logger.info(
            f"--- PERFORMANCE METRICS for {request.method} {request.url.path} ---\n"
            f"Total API Time      : {total_time_ms:.1f} ms\n"
            f"Connection Checkout : {conn_checkout_time_ctx.get():.1f} ms\n"
            f"SQL Execution Time  : {sql_time_ctx.get():.1f} ms\n"
            f"Query Count         : {query_count_ctx.get()}{n_plus_one_str}\n"
            f"Payload Size        : {payload_size / 1024:.1f} KB\n"
            f"JWT Decode Time     : {getattr(request.state, 'jwt_decode_time', 0.0):.1f} ms\n"
            f"Auth DB Time        : {getattr(request.state, 'auth_db_time', 0.0):.1f} ms\n"
            f"-------------------------------------------------------"
        )
        
        return response
