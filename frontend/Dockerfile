# Dockerfile for Agile Predict Frontend
# Multi-stage build for optimized React app
# Runs on localhost on edge nodes, served by Caddy proxy

# Stage 1: Build
FROM node:22-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN if [ -f package-lock.json ]; then \
      npm ci --only=production; \
    else \
      npm install --only=production; \
    fi && \
    npm cache clean --force

# Copy source code
COPY public ./public
COPY src ./src
COPY .env* ./

# Build the app
RUN npm run build

# Stage 2: Runtime
FROM node:22-alpine

WORKDIR /app

# Install serve to run the application locally
RUN npm install -g serve

# Copy built app from builder stage
COPY --from=builder /app/build ./build
COPY --from=builder /app/public ./public

# Create non-root user for security
RUN addgroup -g 1001 -S nodejs && \
    adduser -S nextjs -u 1001

USER nextjs

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Expose port (listens on localhost, Caddy proxies externally)
EXPOSE 3000

# Run the app
CMD ["serve", "-s", "build", "-l", "3000"]
