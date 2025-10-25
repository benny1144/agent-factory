# ---- Stage 1: Build ----
FROM node:18-alpine AS build
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies (use CI-friendly, reproducible install)
RUN npm ci

# Build the production bundle
RUN npm run build


# ---- Stage 2: Runtime ----
FROM node:18-alpine
WORKDIR /app

# Copy build output and minimal runtime files
COPY --from=build /app/dist ./dist
COPY --from=build /app/server.js .
COPY --from=build /app/package*.json ./

# Install only production dependencies
RUN npm install --omit=dev

# Cloud Run expects the container to listen on $PORT (default 8080)
EXPOSE 8080
ENV PORT=8080

# Start the Express server which serves ./dist and binds to $PORT
CMD ["npm", "start"]
