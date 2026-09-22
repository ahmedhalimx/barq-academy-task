# Architecture

The required diagram is [architecture.pdf](../architecture.pdf). It shows the current two-instance loopback stack and labels the recorded final-state transition to three app instances on port 8090. NGINX is the sole public service; apps bridge frontend and backend; PostgreSQL and Redis remain backend-only with persistent storage. The diagram also identifies remaining single points of failure.
